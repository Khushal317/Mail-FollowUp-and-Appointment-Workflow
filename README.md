# AI-Powered Lead Automation & Booking System

## The Real-World Problem It Solves
Businesses often struggle to respond to new leads quickly. A delay of just a few hours can mean losing a customer to a competitor. Furthermore, sales teams waste countless hours manually sending follow-ups to unengaged leads, dealing with back-and-forth scheduling, and managing messy spreadsheets.

This system solves these problems by providing **instant, AI-driven responses** to every new lead, an automated drip-campaign for follow-ups, and a seamless self-service appointment booking system. It ensures that no lead falls through the cracks and allows your sales team to focus entirely on what they do best: closing deals with highly engaged customers who have already booked an appointment.

## The Workflow in Detail
1. **Lead Capture**: A customer submits their details (name, phone, email, and specific requirements) via an API endpoint or web form.
2. **AI Lead Scoring & Initial Contact**: The system immediately evaluates the lead to assign a priority score. Simultaneously, an AI-generated, personalized email is dispatched to the customer asking qualifying questions.
3. **Automated Follow-ups**: If the customer does not reply, the system automatically schedules and sends staggered follow-up emails to keep the conversation alive.
4. **Sales Claiming**: Once a lead replies or engages, they appear in a clean, segregated Active Leads queue. A sales representative can "Claim" the lead to take ownership.
5. **Self-Service Appointment Booking**: The sales representative clicks a single button to generate a secure, unique booking link and emails it to the customer.
6. **Confirmation**: The customer opens the link, views available time slots, and books an appointment. The system prevents double-booking and instantly redirects them to a clean public confirmation page.
7. **Operational Tracking**: The lead is automatically moved from the "Active Leads" queue to a dedicated "Booked Appointments" queue. Once the appointment is fulfilled, it is marked as "Completed," and the sales rep's completion stats are updated on the leaderboard.

## Extensibility for Any Business
While this system is currently configured for a **Solar Panel Installation** business (asking about rooftop sizes and electricity bills), the underlying architecture is completely agnostic. It can be easily tweaked for virtually any service-based business.

**Examples:**
*   **Real Estate**: Ask about preferred neighborhoods, budget, and timeline. Book property viewings.
*   **Home Remodeling / HVAC**: Ask about home square footage and issue types. Book at-home estimates.
*   **Consulting / B2B Services**: Ask about company size and business needs. Book introductory consultation calls.
*   **Automotive Dealerships**: Ask about desired car models and financing options. Book test drives.

## Omnichannel Integration: WhatsApp & Beyond
Currently, the system uses Email for all automated communications and follow-ups. However, the modular background task architecture (powered by Celery) makes it trivial to swap or augment the communication channel. **WhatsApp Business API, SMS (via Twilio), or even automated voice calls** can be integrated directly into the exact same automated workflow based on your specific market demand.

## Tech Stack
*   **Backend**: FastAPI (Python)
*   **Database**: PostgreSQL + SQLAlchemy ORM
*   **Background Jobs**: Celery + Redis (Message Broker)
*   **Frontend**: Vanilla HTML/CSS/JS (Lightweight & Mobile-friendly)

---

## How to Start the Project

### Prerequisites
*   Python 3.9+
*   PostgreSQL installed and running.
*   Redis installed and running.

### Installation & Setup

1. **Navigate to the project directory**:
   ```bash
   cd d:/SolarAutomation
   ```

2. **Install Dependencies**:
   Make sure you have your virtual environment active, then install the required packages. *(e.g., fastapi, uvicorn, sqlalchemy, psycopg2, celery, redis)*

3. **Configure Database**:
   Ensure PostgreSQL is running and you have created the necessary database (the default targets `postgres` on `localhost:5432`). Update the `DATABASE_URL` in `app/database/database.py` or your `.env` file if your credentials differ.

4. **Initialize the Database & Appointment Slots**:
   Run the setup scripts to build the tables and inject test appointment slots:
   ```bash
   python create_tables.py
   python init_slots.py
   ```

### Running the Services
You need to run three separate processes concurrently. Open three terminal windows:

**Terminal 1: Start the FastAPI Server**
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2: Start the Celery Worker (Email & Task Processing)**
```bash
celery -A celery_app worker --loglevel=info --pool=threads --concurrency=4
```

**Terminal 3: Start the Celery Beat Scheduler (Automated Follow-ups)**
```bash
celery -A celery_app beat --loglevel=info
```

### Accessing the System
*   **Sales Dashboard (Active Leads)**: [http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)
*   **Booked Appointments Queue**: [http://127.0.0.1:8000/static/appointments.html](http://127.0.0.1:8000/static/appointments.html)
*   **Completed Sales Leaderboard**: [http://127.0.0.1:8000/static/completed.html](http://127.0.0.1:8000/static/completed.html)
*   **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
