from app.database.database import SessionLocal, engine
from app.models.lead import AppointmentSlot
from datetime import datetime, timedelta

def init_slots():
    db = SessionLocal()
    try:
        # Check if slots already exist
        existing = db.query(AppointmentSlot).count()
        if existing == 0:
            print("Creating static appointment slots for MVP...")
            tomorrow = datetime.now() + timedelta(days=1)
            
            slots = [
                tomorrow.replace(hour=10, minute=0, second=0, microsecond=0),
                tomorrow.replace(hour=13, minute=0, second=0, microsecond=0),
                tomorrow.replace(hour=16, minute=0, second=0, microsecond=0)
            ]
            
            for dt in slots:
                db.add(AppointmentSlot(slot_datetime=dt))
                
            db.commit()
            print("Static slots created successfully.")
        else:
            print(f"Slots already exist ({existing} found).")
    finally:
        db.close()

if __name__ == "__main__":
    init_slots()
