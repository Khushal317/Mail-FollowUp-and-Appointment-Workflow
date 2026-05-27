import asyncio
import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime, timedelta
from app.database.database import SessionLocal
from app.models.lead import Lead, LeadTracking, EmailJob
from app.services.email_service import send_email_async
from app.services.ai_service import generate_auto_reply
from app.utils.logger import logger

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

async def follow_up_cron():
    """Periodically checks leads and sends follow-up emails."""
    logger.info("Follow-up cron started.")
    while True:
        try:
            db = SessionLocal()
            now = datetime.utcnow()
            
            leads = db.query(Lead).join(Lead.tracking).filter(
                LeadTracking.lead_status == "NURTURING",
                LeadTracking.follow_up_stopped == False,
                Lead.assigned_to == None,
                Lead.completed == False
            ).all()

            for lead in leads:
                # TESTING MODE: using minutes instead of days (1min / 3min / 7min)
                minutes_since_created = (now - lead.created_at).total_seconds() / 60
                stage = lead.tracking.follow_up_stage
                
                should_send = False
                template = ""
                new_stage = stage
                
                if minutes_since_created >= 1 and stage < 1:
                    should_send = True
                    new_stage = 1
                    template = f"Hi {lead.full_name}, just checking if you're still interested in reducing your electricity bill with solar."
                elif minutes_since_created >= 3 and stage < 2:
                    should_send = True
                    new_stage = 2
                    template = f"Hi {lead.full_name}, we can provide a free estimate for your property if you'd like."
                elif minutes_since_created >= 7 and stage < 3:
                    should_send = True
                    new_stage = 3
                    template = f"Hi {lead.full_name}, solar subsidy availability may change soon in your area. Let us know if you have any questions!"

                if should_send:
                    logger.info(f"Queueing follow-up {new_stage} to lead {lead.id}")
                    email_job = EmailJob(
                        lead_id=lead.id,
                        email_type=f"FOLLOW_UP_{new_stage}",
                        recipient_email=lead.email,
                        subject="Checking in - Solar Installation",
                        body=template
                    )
                    db.add(email_job)
                    lead.tracking.follow_up_stage = new_stage
                    db.commit()

            db.close()
        except Exception as e:
            logger.error(f"Error in follow-up cron: {e}")
            
        await asyncio.sleep(60) # check every minute

def _sync_imap_poll():
    """Synchronous IMAP polling - runs in a thread to avoid blocking the event loop."""
    import socket
    socket.setdefaulttimeout(15)  # 15-second timeout for all socket operations
    
    matched_leads = []  # collect (lead_id, sender, preview) tuples
    
    mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=15)
    mail.login(SMTP_EMAIL, SMTP_PASSWORD)
    mail.select("inbox")
    
    status, messages = mail.search(None, "UNSEEN")
    if status == "OK" and messages[0]:
        email_ids = messages[0].split()
        db = SessionLocal()
        
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    sender = msg.get("From", "")
                    if "<" in sender:
                        sender = sender.split("<")[1].split(">")[0].strip()
                        
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if "text/plain" in content_type:
                                try:
                                    body = part.get_payload(decode=True).decode()
                                    break
                                except:
                                    pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode()
                        except:
                            body = str(msg.get_payload())
                    
                    preview = body.strip()[:200]
                    
                    lead = db.query(Lead).join(Lead.tracking).filter(
                        Lead.email.ilike(f"%{sender}%"),
                        LeadTracking.lead_status == "NURTURING",
                        Lead.assigned_to == None
                    ).first()
                    
                    if lead:
                        logger.info(f"Reply detected from lead {lead.id}: {sender}")
                        lead.tracking.lead_status = "ENGAGED"
                        lead.tracking.follow_up_stopped = True
                        lead.tracking.last_customer_reply = preview
                        lead.tracking.last_reply_at = datetime.utcnow()
                        db.commit()
                        matched_leads.append((lead.id, lead.email, preview))

        db.close()
    mail.logout()
    return matched_leads


async def imap_polling_cron():
    """Polls IMAP for customer replies using a background thread."""
    logger.info("IMAP Polling cron started.")
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning("No SMTP credentials for IMAP polling.")
        return

    # Initial delay so server can start accepting requests first
    await asyncio.sleep(10)

    while True:
        try:
            # Run all blocking IMAP work in a thread with a timeout
            matched_leads = await asyncio.wait_for(
                asyncio.to_thread(_sync_imap_poll),
                timeout=30
            )
            
            # Queue auto-replies back on the async event loop
            if matched_leads:
                db = SessionLocal()
                for lead_id, lead_email, preview in matched_leads:
                    try:
                        auto_reply = await generate_auto_reply(preview)
                        email_job = EmailJob(
                            lead_id=lead_id,
                            email_type="AUTO_REPLY",
                            recipient_email=lead_email,
                            subject="Re: Your Solar Inquiry",
                            body=auto_reply
                        )
                        db.add(email_job)
                        db.commit()
                        logger.info(f"Queued auto-reply for lead {lead_id}")
                    except Exception as e:
                        logger.error(f"Error queueing auto-reply for lead {lead_id}: {e}")
                db.close()
                    
        except asyncio.TimeoutError:
            logger.warning("IMAP polling timed out after 30s, will retry next cycle.")
        except Exception as e:
            logger.error(f"Error in IMAP polling: {e}")
            
        await asyncio.sleep(30)  # poll every 30 seconds

async def email_worker_cron():
    """Continuously polls the EmailJob table and sends pending emails."""
    logger.info("Email worker started.")
    # Initial delay
    await asyncio.sleep(5)
    
    while True:
        try:
            db = SessionLocal()
            # Find PENDING jobs or FAILED jobs that haven't exhausted retries
            # Process up to 5 jobs per batch to prevent long blocking
            jobs = db.query(EmailJob).filter(
                (EmailJob.status == "PENDING") | 
                ((EmailJob.status == "FAILED") & (EmailJob.retry_count < 3))
            ).limit(5).all()
            
            for job in jobs:
                job.status = "PROCESSING"
                db.commit()
                
                logger.info(f"Worker processing EmailJob {job.id} for lead {job.lead_id} ({job.email_type})")
                
                try:
                    sent = await send_email_async(job.recipient_email, job.subject, job.body)
                    
                    if sent:
                        job.status = "SUCCESS"
                        job.processed_at = datetime.utcnow()
                        logger.info(f"EmailJob {job.id} SUCCESS")
                    else:
                        job.status = "FAILED"
                        job.retry_count += 1
                        job.last_error = "send_email_async returned False"
                        logger.warning(f"EmailJob {job.id} FAILED (Attempt {job.retry_count}/3)")
                        
                except Exception as e:
                    job.status = "FAILED"
                    job.retry_count += 1
                    job.last_error = str(e)
                    logger.error(f"EmailJob {job.id} FAILED with error: {e}")
                
                db.commit()
                
            db.close()
            
            # If we found jobs, sleep a little before next batch. If none, sleep longer.
            if jobs:
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(10)
                
        except Exception as e:
            logger.error(f"Error in email worker: {e}")
            await asyncio.sleep(10)
