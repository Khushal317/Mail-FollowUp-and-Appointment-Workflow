# Lead Automation Demo Platform

A production-style FastAPI demo that helps businesses capture leads, reply instantly, follow up automatically, prioritize interested customers, and book appointments without losing people in the gap between form submission and sales follow-up.

## The Real-World Problem

Many small businesses spend money on ads, websites, social media, or referrals, but still lose leads because the first response is slow or inconsistent.

A customer fills out a form, then waits. The team may be busy, the lead may be missed, or follow-ups may depend on someone remembering to send them. By the time the business responds, the customer may have already gone somewhere else.

This is especially painful for service-based businesses where speed matters:

- Solar companies need to qualify high-bill customers and book site visits.
- Home service teams need to respond quickly to urgent repair requests.
- Local businesses need a simple way to follow up with interested customers.

## The Solution

This project turns a lead form into an automated follow-up workflow.

When a new lead submits a form, the system:

1. Saves the lead in PostgreSQL.
2. Scores and categorizes the lead.
3. Generates a business-aware email reply using Groq.
4. Queues the email through the existing `EmailJob` system.
5. Sends the email through a Celery worker.
6. Schedules follow-ups if the customer does not reply.
7. Detects customer replies through inbox polling.
8. Moves engaged leads higher in the queue.
9. Lets a sales/team member claim the lead.
10. Sends a booking link for an appointment, site visit, or consultation.
11. Tracks booked appointments and completed sales.

The goal is simple: help a business owner understand how automation can prevent lost leads and save manual follow-up time.

## Supported Demo Businesses

The demo supports three business types:

- Solar Company
- Home Services
- Other Business

Each business type has its own form, scoring logic, email style, follow-up copy, and booking wording.

## Core Workflow

```text
Visitor opens landing page
        |
        v
Logs into demo session
        |
        v
Chooses business type
        |
        v
Submits lead form
        |
        v
Lead saved + scored + email job created
        |
        v
Celery sends instant email
        |
        v
Follow-ups are scheduled
        |
        +----------------------------+
        |                            |
        v                            v
Customer replies              No reply yet
        |                            |
        v                            v
Lead moves to engaged queue    Follow-up email is sent
        |
        v
Team claims lead
        |
        v
Team sends booking link
        |
        v
Customer books appointment
        |
        v
Appointment and sales pages update
```

## Key Features

- Public landing page for business owners
- Demo login with temporary session separation
- Business type selection
- Dynamic lead forms for Solar, Home Services, and Other Business
- AI-generated initial email replies using Groq
- PostgreSQL-backed lead storage
- Redis + Celery email job pipeline
- Celery beat follow-up scheduler
- Inbox polling for customer replies
- One-time professional auto-reply after customer engagement
- Lead queue sorted by engagement and value
- Claim flow for sales/team members
- Booking link flow for appointments
- Appointments page for booked customers
- Sales page showing completed appointment counts
- Contact banner and contact page for service inquiries

## Lead Scoring

The system keeps scoring simple and demo-friendly.

Solar leads can become high value when the electricity bill is high or the property is commercial.

Home Services leads can become high value when urgency is emergency or urgent.

Other Business leads can become high value when the automation request is lead-related, urgent, or revenue-focused.

Scores help the team see the most important leads first.

## Email Automation

The system does not send emails directly from the form request.

Instead, it creates an `EmailJob`, then Celery processes that job in the background. This keeps the form fast and makes the automation more reliable.

Email types include:

- Initial reply
- Follow-up 1
- Follow-up 2
- Follow-up 3
- Booking link
- Booking confirmation
- Reply acknowledgment

## Tech Stack

- FastAPI
- PostgreSQL
- Redis
- Celery worker
- Celery beat
- SQLAlchemy
- Groq API
- SMTP email sending
- Static HTML/CSS/JavaScript frontend

## Architecture

```text
FastAPI App
  |
  +-- Static demo pages
  +-- Lead submission API
  +-- Sales queue API
  +-- Appointment API
  |
  +-- PostgreSQL
  |     +-- leads
  |     +-- lead_tracking
  |     +-- email_jobs
  |     +-- appointments
  |     +-- appointment_slots
  |
  +-- Redis
        |
        +-- Celery worker
        +-- Celery beat
```

## Main Pages

- `/` - Public landing page
- `/login` - Simple demo login
- `/demo` - Business type selector
- `/demo/solar` - Solar lead form
- `/demo/home-services` - Home Services lead form
- `/demo/other-business` - Other Business lead form
- `/confirmation` - Lead submission confirmation
- `/static/index.html` - Lead queue
- `/static/appointments.html` - Booked appointments
- `/static/completed.html` - Sales page
- `/contact` - Contact page

## Environment Variables

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/lead_automation
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password

AI_API_KEY=your_groq_api_key
GROQ_API=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

BASE_URL=https://your-hosted-demo-url.com
```

`BASE_URL` is important for hosted booking links. For example, on an EC2 server running directly on port `8000`, use:

```env
BASE_URL=http://YOUR_EC2_PUBLIC_IP:8000
```

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Initialize database tables and appointment slots:

```bash
python create_tables.py
python init_slots.py
```

Start the FastAPI app:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Start Celery worker:

```bash
celery -A celery_app worker --loglevel=info --pool=threads --concurrency=4
```

Start Celery beat:

```bash
celery -A celery_app beat --loglevel=info
```

Open:

```text
http://127.0.0.1:8000
```

## Deployment Notes

For this app to work properly in production, run all required services:

- FastAPI web server
- PostgreSQL database
- Redis broker
- Celery worker
- Celery beat

If only FastAPI is running, the website may load, but background emails and follow-ups will not work correctly.

For AWS EC2 deployment, keep `leadapp`, `celery-worker`, and `celery-beat` running as systemd services.

## Demo Value

This project is built to show a practical automation system, not just a form.

It demonstrates how a business can:

- respond instantly to new leads
- avoid manual follow-up mistakes
- prioritize engaged customers
- let the team claim and handle leads
- move customers from inquiry to appointment
- track completed sales activity

It is a simple but realistic example of how AI and workflow automation can help small businesses convert more leads without adding extra manual work.
