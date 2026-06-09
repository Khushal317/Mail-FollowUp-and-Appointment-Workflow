from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, Optional
from datetime import datetime

class LeadCreate(BaseModel):
    full_name: str
    phone_number: str
    email: EmailStr
    business_type: str = Field(default="SOLAR", pattern="^(SOLAR|HOME_SERVICES|OTHER_BUSINESS)$")
    city: Optional[str] = None
    property_type: Optional[str] = None
    monthly_electricity_bill: Optional[str] = None
    roof_type: Optional[str] = None
    rooftop_size: Optional[str] = None
    installation_timeline: Optional[str] = None
    extra_fields: Dict[str, Any] = Field(default_factory=dict)

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
    business_type: str
    city: Optional[str] = None
    property_type: Optional[str] = None
    monthly_electricity_bill: Optional[str] = None
    roof_type: Optional[str] = None
    rooftop_size: Optional[str] = None
    installation_timeline: Optional[str] = None
    extra_fields: Optional[Dict[str, Any]] = None
    ai_generated_email: Optional[str] = None

    # Original Scoring and Queue fields that stay on Lead
    lead_category: str
    lead_score: int
    lead_status: str
    appointment_status: str
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
