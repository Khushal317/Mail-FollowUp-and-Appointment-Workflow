from app.database.database import engine, Base
from app.models.lead import Lead, LeadTracking, EmailJob

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Creating tables in PostgreSQL...")
Base.metadata.create_all(bind=engine)
print("Done!")
