# Lead Automation Demo Platform

This FastAPI app is a public demo platform for lead follow-up automation across three business types:

- Solar Company
- Home Services
- Other Business

The system keeps the existing architecture: FastAPI, PostgreSQL, Redis, Celery worker, Celery beat, `email_jobs`, automated follow-ups, lead queue, appointment booking, and simple dashboard pages.

## Demo Workflow

1. Open `/`.
2. Click **Try Demo**.
3. Choose a business type at `/demo`.
4. Submit the matching lead form.
5. The app stores the lead, scores it, generates an email with Groq, queues an `EmailJob`, and schedules follow-ups.
6. The team views leads in `/static/index.html`, claims a lead, and sends a booking link.
7. The customer books from `/static/book.html?token=...`.
8. Sales completion counts are visible at `/static/completed.html`.

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

Use `BASE_URL` for hosted booking links. If it is blank, the app uses relative links.

## Run Locally

Install dependencies, then initialize tables and appointment slots:

```bash
pip install -r requirements.txt
python create_tables.py
python init_slots.py
```

Start the API:

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

## Main Pages

- Public landing: `/`
- Business selector: `/demo`
- Solar demo form: `/demo/solar`
- Home Services demo form: `/demo/home-services`
- Other Business demo form: `/demo/other-business`
- Lead queue: `/static/index.html`
- Booked appointments: `/static/appointments.html`
- Sales page: `/static/completed.html`
