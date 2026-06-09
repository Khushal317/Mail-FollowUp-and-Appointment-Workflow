from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.schemas.lead import LeadCreate
from app.database.database import get_db
from app.models.lead import Appointment, EmailJob, Lead, LeadTracking
from app.services.lead_service import process_new_lead
from app.utils.logger import logger

router = APIRouter()


class DemoSessionClearRequest(BaseModel):
    demo_session_id: str


@router.post("/submit-lead", status_code=status.HTTP_200_OK)
def submit_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """Synchronous endpoint - stores lead, queues email, returns immediately."""
    logger.info(f"Received new lead submission for: {lead.email}")
    try:
        return process_new_lead(db, lead)
    except Exception as e:
        logger.error(f"Error processing lead: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the lead.",
        )


@router.post("/test-email-task", status_code=status.HTTP_200_OK)
def test_email_task(db: Session = Depends(get_db)):
    """Manual test route to verify Celery pipeline."""
    logger.info("Received manual test email task request")
    try:
        from app.models.lead import EmailJob
        from app.tasks import send_email_task

        email_job = EmailJob(
            lead_id=9999,
            email_type="TEST",
            recipient_email="test@example.com",
            subject="Test Celery Pipeline",
            body="If you see this, Celery is working.",
        )
        db.add(email_job)
        db.commit()
        db.refresh(email_job)

        logger.info(f"Queued TEST email job {email_job.id}")

        task = send_email_task.delay(email_job.id)

        return {
            "success": True,
            "message": "Test task queued",
            "job_id": email_job.id,
            "celery_task_id": task.id,
        }
    except Exception as e:
        logger.error(f"Error queuing test task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/demo-session/clear", status_code=status.HTTP_200_OK)
def clear_demo_session(request: DemoSessionClearRequest, db: Session = Depends(get_db)):
    """Delete one browser demo session and stop any pending workflow for it."""
    session_id = request.demo_session_id.strip()
    if not session_id:
        return {"success": True, "deleted_leads": 0}

    leads = [
        lead for lead in db.query(Lead).all()
        if lead.extra_fields and lead.extra_fields.get("demo_session_id") == session_id
    ]

    for lead in leads:
        appointments = db.query(Appointment).filter(Appointment.lead_id == lead.id).all()
        for appointment in appointments:
            if appointment.slot:
                appointment.slot.is_booked = False
            db.delete(appointment)

        db.query(EmailJob).filter(EmailJob.lead_id == lead.id).delete(synchronize_session=False)
        db.query(LeadTracking).filter(LeadTracking.lead_id == lead.id).delete(synchronize_session=False)
        db.delete(lead)

    db.commit()
    logger.info(f"Cleared demo session {session_id} ({len(leads)} leads)")
    return {"success": True, "deleted_leads": len(leads)}
