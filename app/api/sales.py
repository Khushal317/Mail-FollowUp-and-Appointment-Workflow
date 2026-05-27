from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import case
from typing import List
from datetime import datetime
from app.database.database import get_db
from app.models.lead import Lead, LeadTracking
from app.schemas.lead import LeadResponse, LeadClaimRequest, LeadCompleteRequest
from app.utils.logger import logger

router = APIRouter(prefix="/sales/leads", tags=["Sales Queue"])

@router.get("", response_model=List[LeadResponse])
def get_active_leads(db: Session = Depends(get_db)):
    """Returns all active non-completed leads sorted by status and category and score."""
    # Custom ordering for category
    category_order = case(
        (Lead.lead_category == 'HIGH_VALUE', 1),
        (Lead.lead_category == 'PRIORITY', 2),
        (Lead.lead_category == 'STANDARD', 3),
        else_=4
    )
    
    status_order = case(
        (LeadTracking.lead_status == 'ENGAGED', 1),
        else_=2
    )
    
    leads = db.query(Lead).join(Lead.tracking)\
        .filter(Lead.completed == False)\
        .order_by(status_order, category_order, Lead.lead_score.desc())\
        .all()
    
    return leads

@router.post("/{lead_id}/claim", response_model=LeadResponse)
def claim_lead(lead_id: int, claim_req: LeadClaimRequest, db: Session = Depends(get_db)):
    """Assigns a lead to a salesperson."""
    lead = db.query(Lead).join(Lead.tracking).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    if lead.assigned_to:
        raise HTTPException(status_code=400, detail="Lead is already claimed")
        
    lead.assigned_to = claim_req.sales_person
    lead.claimed_by_mobile = claim_req.sales_person_mobile
    lead.claimed_at = datetime.utcnow()
    
    # Update tracking
    lead.tracking.lead_status = "CLAIMED"
    lead.tracking.follow_up_stopped = True
    
    db.commit()
    db.refresh(lead)
    logger.info(f"Lead {lead_id} claimed by {claim_req.sales_person} ({claim_req.sales_person_mobile})")
    
    return lead

@router.post("/{lead_id}/complete", response_model=LeadResponse)
def complete_lead(lead_id: int, complete_req: LeadCompleteRequest, db: Session = Depends(get_db)):
    """Marks a lead as completed so it is removed from the active queue."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    if lead.claimed_by_mobile != complete_req.sales_person_mobile:
        raise HTTPException(status_code=403, detail="Only the person who claimed this lead can mark it as complete. Mobile number does not match.")
        
    lead.completed = True
    lead.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(lead)
    logger.info(f"Lead {lead_id} marked as completed")
    
    return lead
