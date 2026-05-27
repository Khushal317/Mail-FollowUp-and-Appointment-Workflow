from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import leads, sales
from app.database.database import engine, Base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Database
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Solar Lead Response System",
    description="Automated lead processing and AI email response generation.",
    version="2.0.0",
)

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

from app.api import leads, sales, appointments

# Include routers
app.include_router(leads.router)
app.include_router(sales.router)
app.include_router(appointments.router)

@app.get("/")
def root():
    return FileResponse("static/submit.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
