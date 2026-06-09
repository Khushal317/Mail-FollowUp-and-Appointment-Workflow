from sqlalchemy import inspect, text
from app.utils.logger import logger


def ensure_demo_columns(engine):
    inspector = inspect(engine)
    if "leads" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("leads")}
    json_type = "JSONB" if engine.dialect.name == "postgresql" else "JSON"

    column_definitions = {
        "business_type": "VARCHAR DEFAULT 'SOLAR'",
        "extra_fields": json_type,
        "lead_category": "VARCHAR DEFAULT 'STANDARD'",
        "lead_score": "INTEGER DEFAULT 0",
        "lead_status": "VARCHAR DEFAULT 'NURTURING'",
        "appointment_status": "VARCHAR DEFAULT 'NOT_SENT'",
    }

    with engine.begin() as conn:
        for name, definition in column_definitions.items():
            if name not in existing:
                logger.info(f"Adding missing leads.{name} column")
                conn.execute(text(f"ALTER TABLE leads ADD COLUMN {name} {definition}"))

        conn.execute(text("UPDATE leads SET business_type = 'SOLAR' WHERE business_type IS NULL"))
        conn.execute(text("UPDATE leads SET lead_category = 'STANDARD' WHERE lead_category IS NULL"))
        conn.execute(text("UPDATE leads SET lead_score = 0 WHERE lead_score IS NULL"))
        conn.execute(text("UPDATE leads SET lead_status = 'NURTURING' WHERE lead_status IS NULL"))
        conn.execute(text("UPDATE leads SET appointment_status = 'NOT_SENT' WHERE appointment_status IS NULL"))
