import os
import smtplib
import imaplib
import email
from email.utils import parseaddr
from datetime import datetime, timedelta
from celery_app import celery
from app.database.database import SessionLocal
from app.models.lead import Lead, LeadTracking, EmailJob
from app.services.email_service import send_email_sync
from app.services.ai_service import generate_email_sync
from app.services.business_service import get_auto_reply_fallback, get_follow_up_body, get_follow_up_subject
from app.services.task_dispatcher import dispatch_task, redis_broker_available
from app.utils.logger import logger

SMTP_EMAIL = os.getenv("SMTP_USER") or os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


@celery.task(name="app.tasks.send_email_task", bind=True, max_retries=3)
def send_email_task(self, job_id: int):
    """Pick up a single EmailJob by ID and send it."""
    db = SessionLocal()
    try:
        job = db.query(EmailJob).filter(EmailJob.id == job_id).first()
        if not job:
            logger.error(f"EmailJob {job_id} not found")
            return

        if job.status == "SUCCESS":
            logger.info(f"EmailJob {job_id} already sent, skipping")
            return

        job.status = "PROCESSING"
        db.commit()

        logger.info(f"Worker processing EmailJob {job.id} for lead {job.lead_id} ({job.email_type})")

        success = send_email_sync(job.recipient_email, job.subject, job.body)

        if success:
            job.status = "SUCCESS"
            job.processed_at = datetime.utcnow()
            job.last_error = None
            
            # Record exact sent time if this is a follow-up
            if job.email_type.startswith("FOLLOW_UP_"):
                tracking = db.query(LeadTracking).filter(LeadTracking.lead_id == job.lead_id).first()
                if tracking:
                    if job.email_type == "FOLLOW_UP_1":
                        tracking.follow_up_1_sent_at = job.processed_at
                    elif job.email_type == "FOLLOW_UP_2":
                        tracking.follow_up_2_sent_at = job.processed_at
                    elif job.email_type == "FOLLOW_UP_3":
                        tracking.follow_up_3_sent_at = job.processed_at

            db.commit()
            logger.info(f"EmailJob {job.id} SUCCESS - sent to {job.recipient_email}")
        else:
            job.retry_count += 1
            job.last_error = "send_email_sync returned False"
            if job.retry_count >= 3:
                job.status = "FAILED"
                logger.error(f"EmailJob {job.id} permanently FAILED after {job.retry_count} attempts")
            else:
                job.status = "PENDING"
                logger.warning(f"EmailJob {job.id} FAILED (Attempt {job.retry_count}/3), will retry")
            db.commit()

    except Exception as e:
        logger.error(f"EmailJob {job_id} error: {e}", exc_info=True)
        if job:
            job.retry_count += 1
            import traceback
            job.last_error = str(traceback.format_exc())[:500]
            if job.retry_count >= 3:
                job.status = "FAILED"
            else:
                job.status = "PENDING"
            db.commit()
    finally:
        db.close()


@celery.task(name="app.tasks.process_email_queue")
def process_email_queue():
    """Find pending EmailJobs and dispatch them to send_email_task workers."""
    db = SessionLocal()
    try:
        jobs = db.query(EmailJob).filter(
            (EmailJob.status == "PENDING") &
            (EmailJob.retry_count < 3)
        ).order_by(EmailJob.created_at).limit(10).all()

        if jobs:
            logger.info(f"Email queue: found {len(jobs)} pending jobs")

        for job in jobs:
            # Mark as PROCESSING immediately to prevent duplicate pickup
            job.status = "PROCESSING"
            db.commit()

            if redis_broker_available():
                dispatch_task(send_email_task, job.id, logger=logger, description=f"Email job {job.id}")
            else:
                send_email_task(job.id)

    except Exception as e:
        logger.error(f"Error in process_email_queue: {e}")
    finally:
        db.close()


@celery.task(name="app.tasks.check_follow_ups")
def check_follow_ups():
    """Check leads and create follow-up EmailJobs using deterministic scheduling."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        from datetime import timedelta
        MIN_GAP = timedelta(minutes=1) # 1 minute spacing constraint for testing

        leads = db.query(Lead).join(Lead.tracking).filter(
            LeadTracking.lead_status == "NURTURING",
            LeadTracking.follow_up_stopped == False,
            Lead.assigned_to == None,
            Lead.completed == False
        ).all()

        for lead in leads:
            tracking = lead.tracking
            stage = tracking.follow_up_stage
            
            should_send = False
            new_stage = stage
            template = ""
            
            # Check for Stage 1
            if stage == 0 and tracking.follow_up_1_scheduled_at and now >= tracking.follow_up_1_scheduled_at:
                logger.info(f"Lead {lead.id} eligible for FU_1. Scheduled at: {tracking.follow_up_1_scheduled_at}")
                should_send = True
                new_stage = 1
                template = get_follow_up_body(lead, new_stage)
            
            # Check for Stage 2
            elif stage == 1 and tracking.follow_up_2_scheduled_at and now >= tracking.follow_up_2_scheduled_at:
                if tracking.follow_up_1_sent_at and (now >= tracking.follow_up_1_sent_at + MIN_GAP):
                    logger.info(f"Lead {lead.id} eligible for FU_2. Scheduled at: {tracking.follow_up_2_scheduled_at}. Spacing validated.")
                    should_send = True
                    new_stage = 2
                    template = get_follow_up_body(lead, new_stage)
                else:
                    logger.warning(f"Lead {lead.id} eligible for FU_2 but blocked by spacing rule. Rescheduling slightly later.")
                    
            # Check for Stage 3
            elif stage == 2 and tracking.follow_up_3_scheduled_at and now >= tracking.follow_up_3_scheduled_at:
                if tracking.follow_up_2_sent_at and (now >= tracking.follow_up_2_sent_at + MIN_GAP):
                    logger.info(f"Lead {lead.id} eligible for FU_3. Scheduled at: {tracking.follow_up_3_scheduled_at}. Spacing validated.")
                    should_send = True
                    new_stage = 3
                    template = get_follow_up_body(lead, new_stage)
                else:
                    logger.warning(f"Lead {lead.id} eligible for FU_3 but blocked by spacing rule. Rescheduling slightly later.")

            if should_send:
                # Re-check lead state from DB to prevent race conditions
                fresh_tracking = db.query(LeadTracking).filter(LeadTracking.lead_id == lead.id).first()
                if fresh_tracking and fresh_tracking.follow_up_stopped:
                    logger.info(f"Follow-up {new_stage} skipped for lead {lead.id} - already stopped.")
                    continue

                logger.info(f"Queueing follow-up {new_stage} to lead {lead.id}.")
                email_job = EmailJob(
                    lead_id=lead.id,
                    email_type=f"FOLLOW_UP_{new_stage}",
                    recipient_email=lead.email,
                    subject=get_follow_up_subject(lead.business_type),
                    body=template
                )
                db.add(email_job)
                fresh_tracking.follow_up_stage = new_stage
                db.commit()

                dispatch_task(send_email_task, email_job.id, logger=logger, description=f"Follow-up email job {email_job.id}")

    except Exception as e:
        logger.error(f"Error in check_follow_ups: {e}", exc_info=True)
    finally:
        db.close()


@celery.task(name="app.tasks.poll_inbox")
def poll_inbox():
    """Poll IMAP inbox for customer replies. Runs via Celery Beat every 60s."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning("No SMTP credentials for IMAP polling.")
        return

    logger.info("IMAP polling task started.")

    try:
        import socket
        socket.setdefaulttimeout(15)

        mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=15)
        mail.login(SMTP_EMAIL, SMTP_PASSWORD)
        mail.select("inbox")

        since_date = (datetime.utcnow() - timedelta(days=1)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, "SINCE", since_date)
        if status == "OK" and messages[0]:
            email_ids = messages[0].split()
            db = SessionLocal()

            for e_id in email_ids:
                res, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        sender = parseaddr(msg.get("From", ""))[1].strip().lower()
                        if not sender or sender == (SMTP_EMAIL or "").lower():
                            continue

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
                            Lead.email.ilike(sender),
                            LeadTracking.lead_status == "NURTURING",
                            Lead.completed == False
                        ).order_by(Lead.id.desc()).first()

                        if not lead:
                            lead = db.query(Lead).join(Lead.tracking).filter(
                                Lead.email.ilike(sender),
                                LeadTracking.lead_status.in_(["NURTURING", "CLAIMED", "COMPLETED"])
                            ).order_by(Lead.id.desc()).first()

                        if lead:
                            logger.info(f"Reply detected from lead {lead.id}: {sender}")
                            existing_auto_reply = db.query(EmailJob).filter(
                                EmailJob.lead_id == lead.id,
                                EmailJob.email_type == "AUTO_REPLY",
                            ).first()
                            lead.tracking.lead_status = "ENGAGED"
                            lead.lead_status = "ENGAGED"
                            lead.completed = False
                            lead.completed_at = None
                            lead.tracking.follow_up_stopped = True
                            lead.tracking.last_customer_reply = preview
                            lead.tracking.last_reply_at = datetime.utcnow()
                            db.commit()

                            # Queue auto-reply
                            if existing_auto_reply:
                                logger.info(f"Auto-reply already exists for lead {lead.id}; skipping duplicate.")
                                continue

                            try:
                                auto_reply = get_auto_reply_fallback(lead.business_type)
                                email_job = EmailJob(
                                    lead_id=lead.id,
                                    email_type="AUTO_REPLY",
                                    recipient_email=lead.email,
                                    subject="Re: Your Inquiry",
                                    body=auto_reply
                                )
                                db.add(email_job)
                                db.commit()
                                logger.info(f"Queued auto-reply for lead {lead.id}")
                                dispatch_task(send_email_task, email_job.id, logger=logger, description=f"Auto-reply email job {email_job.id}")
                            except Exception as e:
                                logger.error(f"Error queueing auto-reply for lead {lead.id}: {e}")

            db.close()
        mail.logout()
        logger.info("IMAP polling task completed.")

    except Exception as e:
        logger.error(f"Error in poll_inbox: {e}")
