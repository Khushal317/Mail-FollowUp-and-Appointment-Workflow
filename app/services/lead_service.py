from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.lead import Lead, LeadTracking, EmailJob
from app.schemas.lead import LeadCreate
from app.services.ai_service import generate_email_sync
from app.services.business_service import (
    get_fallback_initial_email,
    get_initial_subject,
    normalize_business_type,
)
from app.services.scoring_service import calculate_lead_score
from app.services.task_dispatcher import dispatch_task
from app.utils.logger import logger


def _clean_extra_fields(lead_data: LeadCreate):
    extra = dict(lead_data.extra_fields or {})

    if lead_data.business_type == "SOLAR":
        extra["monthly_electricity_bill"] = lead_data.monthly_electricity_bill or extra.get("monthly_electricity_bill")
        extra["property_type"] = lead_data.property_type or extra.get("property_type")
        extra["city"] = lead_data.city or extra.get("city")

    return {key: value for key, value in extra.items() if value not in [None, ""]}


def process_new_lead(db: Session, lead_data: LeadCreate):
    """Store the lead, queue initial email, and schedule follow-ups."""
    lead_data.business_type = normalize_business_type(lead_data.business_type)
    score, category = calculate_lead_score(lead_data)

    lead_dict = lead_data.model_dump()
    lead_dict["extra_fields"] = _clean_extra_fields(lead_data)
    lead_dict["lead_score"] = score
    lead_dict["lead_category"] = category
    lead_dict["lead_status"] = "NURTURING"
    lead_dict["appointment_status"] = "NOT_SENT"
    lead_dict["completed"] = False

    db_lead = Lead(**lead_dict)

    now = datetime.utcnow()
    db_tracking = LeadTracking(
        lead_status="NURTURING",
        follow_up_stopped=False,
        follow_up_1_scheduled_at=now + timedelta(minutes=1),
        follow_up_2_scheduled_at=now + timedelta(minutes=3),
        follow_up_3_scheduled_at=now + timedelta(minutes=7),
    )
    db_lead.tracking = db_tracking

    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    logger.info(f"Stored new {db_lead.business_type} lead in database with ID: {db_lead.id}")

    try:
        email_content = generate_email_sync(lead_data)
    except Exception:
        logger.warning("Falling back to template email due to AI service failure.")
        email_content = get_fallback_initial_email(lead_data)

    email_job = EmailJob(
        lead_id=db_lead.id,
        email_type="INITIAL",
        recipient_email=db_lead.email,
        subject=get_initial_subject(db_lead.business_type),
        body=email_content,
    )
    db.add(email_job)

    if email_content:
        db_lead.ai_generated_email = email_content

    db.commit()
    db.refresh(db_lead)
    logger.info(f"Queued initial email job for lead {db_lead.id}")

    from app.tasks import send_email_task

    dispatch_task(send_email_task, email_job.id, logger=logger, description=f"Email job {email_job.id}")

    return {
        "success": True,
        "message": "Lead submitted successfully",
        "lead_id": db_lead.id,
        "email_queued": True,
    }
