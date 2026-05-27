#!/bin/bash

# Initialize the database (creates tables if they don't exist)
python create_tables.py
python init_slots.py

# Start Celery Worker in the background
celery -A celery_app worker --loglevel=info --pool=threads --concurrency=4 &

# Start Celery Beat in the background
celery -A celery_app beat --loglevel=info &

# Start FastAPI web server (PORT is provided by Render)
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
