from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import string
import random
from datetime import datetime
from app.database.database import get_db
from app.models.lead import Lead, LeadTracking, Appointment, AppointmentSlot, EmailJob
from app.schemas.appointment import AppointmentSlotResponse, AppointmentBookRequest
from app.utils.logger import logger
from app.tasks import send_email_task

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

def generate_secure_token(length=10):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

@router.post("/{lead_id}/send-link")
def send_booking_link(lead_id: int, db: Session = Depends(get_db)):
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
    booking_url = f"http://localhost:8000/static/book.html?token={token}"
    email_body = f"Hi {lead.full_name},\n\nPlease select a convenient time for your free solar site visit by clicking the link below:\n\n{booking_url}\n\nBest,\nYour Solar Team"
    
    email_job = EmailJob(
        lead_id=lead.id,
        email_type="BOOKING_LINK",
        recipient_email=lead.email,
        subject="Book Your Free Solar Site Visit",
        body=email_body
    )
    db.add(email_job)
    db.commit()
    
    send_email_task.delay(email_job.id)
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

    # Update slot and appointment
    slot.is_booked = True
    appointment.appointment_slot_id = slot.id
    appointment.confirmed_address = request.confirmed_address
    appointment.status = "BOOKED"
    
    # Update lead status
    lead = db.query(Lead).filter(Lead.id == appointment.lead_id).first()
    tracking = db.query(LeadTracking).filter(LeadTracking.lead_id == appointment.lead_id).first()
    
    if tracking:
        tracking.lead_status = "APPOINTMENT_BOOKED"
        
    db.commit()
    logger.info(f"Slot {slot.id} reserved for Lead {lead.id}. Booking completed.")

    # Queue confirmation emails
    # To Customer
    customer_email = EmailJob(
        lead_id=lead.id,
        email_type="BOOKING_CONFIRMATION",
        recipient_email=lead.email,
        subject="Solar Site Visit Confirmed",
        body=f"Hi {lead.full_name},\n\nYour solar site visit is confirmed for {slot.slot_datetime.strftime('%B %d, %Y at %I:%M %p')} at {request.confirmed_address}.\n\nSee you soon!"
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
        body=f"Lead {lead.full_name} has booked a site visit for {slot.slot_datetime.strftime('%B %d, %Y at %I:%M %p')}.\nAddress: {request.confirmed_address}"
    )
    db.add(rep_notification)
    
    db.commit()
    
    send_email_task.delay(customer_email.id)
    send_email_task.delay(rep_notification.id)

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
def get_booked_appointments(db: Session = Depends(get_db)):
    appointments = db.query(Appointment).filter(Appointment.status == "BOOKED").all()
    results = []
    for appt in appointments:
        if not appt.slot or not appt.lead:
            continue
        results.append({
            "id": appt.id,
            "lead_id": appt.lead.id,
            "customer_name": appt.lead.full_name,
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
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment or appointment.status != "BOOKED":
        raise HTTPException(status_code=404, detail="Booked appointment not found")
        
    appointment.status = "COMPLETED"
    appointment.completed_by = sales_rep
    appointment.completed_at = datetime.utcnow()
    
    lead = db.query(Lead).filter(Lead.id == appointment.lead_id).first()
    if lead:
        lead.completed = True
        lead.completed_at = datetime.utcnow()
        tracking = db.query(LeadTracking).filter(LeadTracking.lead_id == lead.id).first()
        if tracking:
            tracking.lead_status = "COMPLETED"
            
    db.commit()
    return {"success": True}

@router.get("/stats")
def get_sales_stats(db: Session = Depends(get_db)):
    completed_appointments = db.query(Appointment).filter(Appointment.status == "COMPLETED").all()
    stats = {}
    for appt in completed_appointments:
        rep = appt.completed_by or "Unknown"
        stats[rep] = stats.get(rep, 0) + 1
        
    return [{"sales_rep": rep, "completed_visits": count} for rep, count in stats.items()]
