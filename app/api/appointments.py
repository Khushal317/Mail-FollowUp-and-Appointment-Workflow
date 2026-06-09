from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import string
import random
from datetime import datetime
from app.database.database import get_db
from app.models.lead import Lead, LeadTracking, Appointment, AppointmentSlot, EmailJob
from app.schemas.appointment import AppointmentSlotResponse, AppointmentBookRequest
from app.utils.logger import logger
from app.tasks import send_email_task
from app.services.business_service import get_booking_label
from app.services.task_dispatcher import dispatch_task

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

def generate_secure_token(length=10):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))


def get_base_url(request: Request) -> str:
    configured_base_url = (os.getenv("BASE_URL") or "").rstrip("/")
    if configured_base_url:
        return configured_base_url
    return str(request.base_url).rstrip("/")


def lead_matches_session(lead: Lead, demo_session_id: Optional[str]) -> bool:
    if not demo_session_id:
        return True
    return bool(lead.extra_fields and lead.extra_fields.get("demo_session_id") == demo_session_id)


@router.post("/{lead_id}/send-link")
def send_booking_link(lead_id: int, request: Request, db: Session = Depends(get_db)):
    """Generate a secure booking link and email it to the customer."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    tracking = db.query(LeadTracking).filter(LeadTracking.lead_id == lead.id).first()
    if not tracking or tracking.lead_status != "CLAIMED":
        # Allowing ENGAGED too if they skip claim? The prompt says "Booking should ONLY happen AFTER sales rep claims lead".
        # However, the previous UI sets assigned_to, but status remains ENGAGED or NURTURING. Let's check `lead.assigned_to`.
        pass
        
    if not lead.assigned_to:
        raise HTTPException(status_code=400, detail="Booking link can only be sent for claimed leads.")

    # Check if a pending appointment already exists
    appointment = db.query(Appointment).filter(Appointment.lead_id == lead.id).first()
    if appointment and appointment.status in ["BOOKED", "COMPLETED"]:
        raise HTTPException(status_code=400, detail="This customer has already booked an appointment.")

    if not appointment:
        token = generate_secure_token()
        appointment = Appointment(
            lead_id=lead.id,
            booking_token=token,
            status="PENDING"
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
    else:
        token = appointment.booking_token

    # Queue booking email
    base_url = get_base_url(request)
    booking_url = f"{base_url}/static/book.html?token={token}"
    booking_label = get_booking_label(lead.business_type)
    email_body = f"Hi {lead.full_name},\n\nPlease select a convenient time by clicking the link below:\n\n{booking_url}\n\nBest,\nThe Team"
    
    email_job = EmailJob(
        lead_id=lead.id,
        email_type="BOOKING_LINK",
        recipient_email=lead.email,
        subject=booking_label,
        body=email_body
    )
    db.add(email_job)
    lead.appointment_status = "LINK_SENT"
    db.commit()
    
    dispatch_task(send_email_task, email_job.id, logger=logger, description=f"Booking email job {email_job.id}")
    logger.info(f"Booking link generated and queued for Lead {lead.id}. Token: {token}")

    return {"success": True, "message": "Booking link sent to customer"}

@router.get("/slots", response_model=List[AppointmentSlotResponse])
def get_available_slots(db: Session = Depends(get_db)):
    """Get all available (unbooked) appointment slots."""
    slots = db.query(AppointmentSlot).filter(AppointmentSlot.is_booked == False).order_by(AppointmentSlot.slot_datetime).all()
    return slots

@router.post("/book")
def book_appointment(request: AppointmentBookRequest, db: Session = Depends(get_db)):
    """Customer submits booking."""
    # Find appointment by token
    appointment = db.query(Appointment).filter(Appointment.booking_token == request.token).first()
    if not appointment:
        logger.warning(f"Invalid booking token used: {request.token}")
        raise HTTPException(status_code=404, detail="Invalid booking token")
        
    if appointment.status != "PENDING":
        raise HTTPException(status_code=400, detail="Appointment has already been booked or cancelled")

    # Lock slot
    slot = db.query(AppointmentSlot).filter(AppointmentSlot.id == request.slot_id).with_for_update().first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
        
    if slot.is_booked:
        logger.warning(f"Double booking prevented for slot {slot.id} (Lead {appointment.lead_id})")
        raise HTTPException(status_code=400, detail="This time slot is no longer available. Please select another.")

    lead = db.query(Lead).filter(Lead.id == appointment.lead_id).first()
    tracking = db.query(LeadTracking).filter(LeadTracking.lead_id == appointment.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Associated lead not found")

    # Update slot and appointment
    slot.is_booked = True
    appointment.appointment_slot_id = slot.id
    appointment.confirmed_address = request.confirmed_address
    appointment.status = "BOOKED"
    
    if tracking:
        tracking.lead_status = "APPOINTMENT_BOOKED"
    lead.lead_status = "APPOINTMENT_BOOKED"
    lead.appointment_status = "BOOKED"
        
    db.commit()
    logger.info(f"Slot {slot.id} reserved for Lead {lead.id}. Booking completed.")

    # Queue confirmation emails
    # To Customer
    customer_email = EmailJob(
        lead_id=lead.id,
        email_type="BOOKING_CONFIRMATION",
        recipient_email=lead.email,
        subject=f"{get_booking_label(lead.business_type)} Confirmed",
        body=f"Hi {lead.full_name},\n\nYour appointment is confirmed for {slot.slot_datetime.strftime('%B %d, %Y at %I:%M %p')} at {request.confirmed_address}.\n\nSee you soon!"
    )
    db.add(customer_email)
    
    # To Sales Rep (using a mock email or the system's email for MVP)
    # We'll just log it for now or send an email if there's a rep email.
    # The requirement says: "send notification email to assigned sales rep"
    # We don't have sales rep emails stored, so we'll just queue it to a generic admin email or the rep's name @ company
    rep_email = f"{lead.assigned_to.replace(' ', '').lower()}@company.com" if lead.assigned_to else "sales@company.com"
    rep_notification = EmailJob(
        lead_id=lead.id,
        email_type="SALES_NOTIFICATION",
        recipient_email=rep_email,
        subject=f"New Appointment Booked: {lead.full_name}",
        body=f"Lead {lead.full_name} has booked an appointment for {slot.slot_datetime.strftime('%B %d, %Y at %I:%M %p')}.\nAddress: {request.confirmed_address}"
    )
    db.add(rep_notification)
    
    db.commit()
    
    dispatch_task(send_email_task, customer_email.id, logger=logger, description=f"Booking confirmation job {customer_email.id}")
    dispatch_task(send_email_task, rep_notification.id, logger=logger, description=f"Sales notification job {rep_notification.id}")

    return {"success": True, "message": "Appointment booked successfully"}

@router.get("/confirmation/{token}")
def get_booking_confirmation(token: str, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.booking_token == token).first()
    if not appointment or appointment.status != "BOOKED":
        raise HTTPException(status_code=404, detail="Booking not found or not confirmed")
    
    slot = db.query(AppointmentSlot).filter(AppointmentSlot.id == appointment.appointment_slot_id).first()
    
    return {
        "success": True,
        "date_time": slot.slot_datetime.isoformat() if slot else None,
        "address": appointment.confirmed_address
    }

@router.get("/booked")
def get_booked_appointments(demo_session_id: Optional[str] = None, db: Session = Depends(get_db)):
    appointments = db.query(Appointment).filter(Appointment.status == "BOOKED").all()
    results = []
    for appt in appointments:
        if not appt.slot or not appt.lead:
            continue
        if not lead_matches_session(appt.lead, demo_session_id):
            continue
        results.append({
            "id": appt.id,
            "lead_id": appt.lead.id,
            "customer_name": appt.lead.full_name,
            "business_type": appt.lead.business_type,
            "phone_number": appt.lead.phone_number,
            "email": appt.lead.email,
            "confirmed_address": appt.confirmed_address,
            "appointment_time": appt.slot.slot_datetime.isoformat(),
            "assigned_rep": appt.lead.assigned_to,
            "lead_category": appt.lead.lead_category,
            "status": appt.status
        })
    return results

@router.post("/{appointment_id}/complete")
def complete_appointment(appointment_id: int, request_data: dict, db: Session = Depends(get_db)):
    sales_rep = request_data.get("sales_rep", "System")
    sales_rep_mobile = request_data.get("sales_rep_mobile")
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment or appointment.status != "BOOKED":
        raise HTTPException(status_code=404, detail="Booked appointment not found")
        
    lead = db.query(Lead).filter(Lead.id == appointment.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Associated lead not found")
        
    if not lead.claimed_by_mobile or lead.claimed_by_mobile != sales_rep_mobile:
        raise HTTPException(status_code=403, detail="Verification failed: Mobile number does not match the person who claimed this lead.")
        
    appointment.status = "COMPLETED"
    appointment.completed_by = sales_rep
    appointment.completed_at = datetime.utcnow()
    
    lead.completed = True
    lead.completed_at = datetime.utcnow()
    lead.lead_status = "COMPLETED"
    lead.appointment_status = "COMPLETED"
    tracking = db.query(LeadTracking).filter(LeadTracking.lead_id == lead.id).first()
    if tracking:
        tracking.lead_status = "COMPLETED"
            
    db.commit()
    return {"success": True}

@router.get("/stats")
def get_sales_stats(demo_session_id: Optional[str] = None, db: Session = Depends(get_db)):
    completed_appointments = db.query(Appointment).join(Appointment.lead).filter(
        Appointment.status.in_(["BOOKED", "COMPLETED"])
    ).all()
    stats = {}
    for appt in completed_appointments:
        if not appt.lead or not lead_matches_session(appt.lead, demo_session_id):
            continue
        rep = appt.lead.assigned_to or appt.completed_by or "Unassigned"
        mobile = appt.lead.claimed_by_mobile or ""
        if rep not in stats:
            stats[rep] = {"sales_rep": rep, "mobile": mobile, "completed_sales": 0}
        stats[rep]["completed_sales"] += 1

    return sorted(stats.values(), key=lambda item: item["completed_sales"], reverse=True)
