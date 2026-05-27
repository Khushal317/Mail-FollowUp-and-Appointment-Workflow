import os
from dotenv import load_dotenv
import psycopg2
from redis import Redis

# Load .env
load_dotenv()

db_url = os.getenv("DATABASE_URL")
broker_url = os.getenv("CELERY_BROKER_URL")

print(f"DATABASE_URL: {db_url}")
print(f"CELERY_BROKER_URL: {broker_url}")

if "sqlite" in str(db_url).lower():
    print("ERROR: SQLite URL found!")
else:
    print("SUCCESS: Not using SQLite.")

# Check DB connection and tables
try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"PostgreSQL Connection SUCCESS. Tables found: {tables}")
    if "leads" in tables and "email_jobs" in tables:
        print("SUCCESS: Required tables exist.")
    else:
        print("ERROR: Missing required tables!")
    conn.close()
except Exception as e:
    print(f"DB Connection ERROR: {e}")

# Check Redis connection
try:
    r = Redis.from_url(broker_url)
    r.ping()
    print("Redis Connection SUCCESS.")
except Exception as e:
    print(f"Redis Connection ERROR: {e}")
