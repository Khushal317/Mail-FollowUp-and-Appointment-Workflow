from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.lead import LeadCreate
from app.database.database import get_db
from app.services.lead_service import process_new_lead
from app.utils.logger import logger

router = APIRouter()

@router.post("/submit-lead", status_code=status.HTTP_200_OK)
def submit_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """Synchronous endpoint — stores lead, queues email, returns immediately."""
    logger.info(f"Received new lead submission for: {lead.email}")
    try:
        result = process_new_lead(db, lead)
        return {"success": True, "message": "Lead submitted successfully"}
    except Exception as e:
        logger.error(f"Error processing lead: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the lead."
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
            body="If you see this, Celery is working."
        )
        db.add(email_job)
        db.commit()
        db.refresh(email_job)
        
        logger.info(f"Queued TEST email job {email_job.id}")
        
        # Enqueue task
        task = send_email_task.delay(email_job.id)
        
        return {
            "success": True, 
            "message": "Test task queued", 
            "job_id": email_job.id, 
            "celery_task_id": task.id
        }
    except Exception as e:
        logger.error(f"Error queuing test task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
