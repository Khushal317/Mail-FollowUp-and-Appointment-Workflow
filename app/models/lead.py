from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    phone_number = Column(String)
    email = Column(String, index=True)
    city = Column(String)
    property_type = Column(String)
    monthly_electricity_bill = Column(String)
    roof_type = Column(String)
    rooftop_size = Column(String)
    installation_timeline = Column(String)
    ai_generated_email = Column(String, nullable=True)
    
    # Scoring and Queue Fields
    lead_category = Column(String, index=True) # HIGH_VALUE, PRIORITY, STANDARD
    lead_score = Column(Integer, index=True)
    assigned_to = Column(String, nullable=True)
    claimed_by_mobile = Column(String, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False, index=True) 
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to Tracking
    tracking = relationship("LeadTracking", back_populates="lead", uselist=False, cascade="all, delete-orphan")

class LeadTracking(Base):
    __tablename__ = "lead_tracking"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), unique=True)
    lead_status = Column(String, default="NURTURING", index=True) # NEW, NURTURING, ENGAGED, CLAIMED, COMPLETED
    last_customer_reply = Column(String, nullable=True)
    last_reply_at = Column(DateTime, nullable=True)
    follow_up_stage = Column(Integer, default=0)
    follow_up_stopped = Column(Boolean, default=False)
    
    # Deterministic Scheduling Fields
    follow_up_1_scheduled_at = Column(DateTime, nullable=True)
    follow_up_2_scheduled_at = Column(DateTime, nullable=True)
    follow_up_3_scheduled_at = Column(DateTime, nullable=True)
    
    follow_up_1_sent_at = Column(DateTime, nullable=True)
    follow_up_2_sent_at = Column(DateTime, nullable=True)
    follow_up_3_sent_at = Column(DateTime, nullable=True)

    lead = relationship("Lead", back_populates="tracking")

class EmailJob(Base):
    __tablename__ = "email_jobs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, index=True)
    email_type = Column(String) # e.g. INITIAL, FOLLOW_UP_1, AUTO_REPLY
    recipient_email = Column(String, index=True)
    subject = Column(String)
    body = Column(String)
    status = Column(String, default="PENDING", index=True) # PENDING, PROCESSING, SUCCESS, FAILED
    retry_count = Column(Integer, default=0)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class AppointmentSlot(Base):
    __tablename__ = "appointment_slots"

    id = Column(Integer, primary_key=True, index=True)
    slot_datetime = Column(DateTime, nullable=False, index=True)
    is_booked = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True)
    booking_token = Column(String, unique=True, index=True, nullable=False)
    appointment_slot_id = Column(Integer, ForeignKey("appointment_slots.id"), nullable=True)
    confirmed_address = Column(String, nullable=True)
    status = Column(String, default="PENDING", index=True) # PENDING, BOOKED, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_by = Column(String, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    lead = relationship("Lead")
    slot = relationship("AppointmentSlot")
