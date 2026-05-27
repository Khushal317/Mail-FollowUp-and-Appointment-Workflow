from app.database.database import engine, Base
from app.models.lead import Lead, LeadTracking, EmailJob, Appointment, AppointmentSlot

print("Creating tables in PostgreSQL (if not exist)...")
Base.metadata.create_all(bind=engine)
print("Done!")
