import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import leads, sales
from app.database.database import engine, Base
from app.database.schema_sync import ensure_demo_columns
from app.services.local_worker import run_local_email_worker
from app.services.task_dispatcher import redis_broker_available
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Database
Base.metadata.create_all(bind=engine)
ensure_demo_columns(engine)

app = FastAPI(
    title="Lead Automation Demo Platform",
    description="Multi-business lead capture, email follow-up, and appointment booking demo.",
    version="2.0.0",
)

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

from app.api import leads, sales, appointments

# Include routers
app.include_router(leads.router)
app.include_router(sales.router)
app.include_router(appointments.router)


@app.on_event("startup")
async def start_local_worker_fallback():
    if not redis_broker_available():
        app.state.local_worker_task = asyncio.create_task(run_local_email_worker())


@app.get("/")
def root():
    return FileResponse("static/landing.html")

@app.get("/demo")
def demo_selector():
    return FileResponse("static/demo.html")

@app.get("/login")
def login():
    return FileResponse("static/login.html")

@app.get("/demo/{business_slug}")
def demo_form(business_slug: str):
    return FileResponse("static/demo-form.html")

@app.get("/confirmation")
def confirmation():
    return FileResponse("static/confirmation.html")

@app.get("/contact")
def contact():
    return FileResponse("static/contact.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
