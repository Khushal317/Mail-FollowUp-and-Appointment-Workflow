from sqlalchemy.orm import Session
from app.models.lead import Lead, LeadTracking, EmailJob
from app.schemas.lead import LeadCreate
from app.services.ai_service import generate_email_sync
from app.services.email_service import get_fallback_email
from app.utils.logger import logger
from app.services.scoring_service import calculate_lead_score


def process_new_lead(db: Session, lead_data: LeadCreate):
    """Process a new lead submission. Fully synchronous — no async needed."""
    # 1. Calculate Score and Category
    score, category = calculate_lead_score(lead_data)

    # 2. Store lead in DB
    lead_dict = lead_data.model_dump()
    lead_dict["lead_score"] = score
    lead_dict["lead_category"] = category
    lead_dict["completed"] = False

    db_lead = Lead(**lead_dict)

    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    # Add initial tracking record with deterministic scheduled timestamps
    # For testing: 1 min, 3 min, 7 min
    db_tracking = LeadTracking(
        lead_status="NURTURING", 
        follow_up_stopped=False,
        follow_up_1_scheduled_at=now + timedelta(minutes=1),
        follow_up_2_scheduled_at=now + timedelta(minutes=3),
        follow_up_3_scheduled_at=now + timedelta(minutes=7)
    )
    db_lead.tracking = db_tracking

    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    logger.info(f"Stored new lead in database with ID: {db_lead.id}")

    # 3. Generate email content
    email_content = None
    try:
        email_content = generate_email_sync(lead_data)
    except Exception as e:
        logger.warning("Falling back to template email due to AI service failure.")
        email_content = get_fallback_email(lead_data.full_name)

    # 4. Queue Email Job
    subject = "Thanks for Your Solar Inquiry — Next Steps"
    email_job = EmailJob(
        lead_id=db_lead.id,
        email_type="INITIAL",
        recipient_email=db_lead.email,
        subject=subject,
        body=email_content
    )
    db.add(email_job)

    # 5. Update lead with generated email content
    if email_content:
        db_lead.ai_generated_email = email_content

    db.commit()
    db.refresh(db_lead)
    logger.info(f"Queued initial email job for lead {db_lead.id}")

    # 6. Dispatch to Celery worker immediately
    from app.tasks import send_email_task
    send_email_task.delay(email_job.id)

    return {
        "success": True,
        "message": "Lead submitted successfully",
        "lead_id": db_lead.id,
        "email_queued": True
    }
