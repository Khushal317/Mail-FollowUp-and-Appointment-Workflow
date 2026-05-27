from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class AppointmentSlotBase(BaseModel):
    slot_datetime: datetime
    is_booked: bool

class AppointmentSlotResponse(AppointmentSlotBase):
    id: int
    
    class Config:
        orm_mode = True
        from_attributes = True

class AppointmentBookRequest(BaseModel):
    token: str
    slot_id: int
    confirmed_address: str

class AppointmentResponse(BaseModel):
    id: int
    lead_id: int
    booking_token: str
    appointment_slot_id: Optional[int]
    confirmed_address: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True
