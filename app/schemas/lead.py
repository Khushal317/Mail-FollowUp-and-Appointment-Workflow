from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class LeadCreate(BaseModel):
    full_name: str
    phone_number: str
    email: EmailStr
    city: str
    property_type: str
    monthly_electricity_bill: str
    roof_type: str
    rooftop_size: str
    installation_timeline: str

class LeadResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    email: EmailStr
    city: str
    property_type: str
    monthly_electricity_bill: str
    roof_type: str
    rooftop_size: str
    installation_timeline: str
    ai_generated_email: Optional[str] = None
    
class LeadTrackingResponse(BaseModel):
    id: int
    lead_status: str
    last_customer_reply: Optional[str] = None
    last_reply_at: Optional[datetime] = None
    follow_up_stage: int
    follow_up_stopped: bool
    
    class Config:
        from_attributes = True

class LeadResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    email: EmailStr
    city: str
    property_type: str
    monthly_electricity_bill: str
    roof_type: str
    rooftop_size: str
    installation_timeline: str
    ai_generated_email: Optional[str] = None
    
    # Original Scoring and Queue fields that stay on Lead
    lead_category: str
    lead_score: int
    assigned_to: Optional[str] = None
    claimed_by_mobile: Optional[str] = None
    claimed_at: Optional[datetime] = None
    completed: bool
    completed_at: Optional[datetime] = None
    
    created_at: datetime
    
    # Nested Tracking Data
    tracking: Optional[LeadTrackingResponse] = None

    class Config:
        from_attributes = True

class LeadClaimRequest(BaseModel):
    sales_person: str
    sales_person_mobile: str

class LeadCompleteRequest(BaseModel):
    sales_person_mobile: str
