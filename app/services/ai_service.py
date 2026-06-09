import os
from openai import OpenAI
from app.schemas.lead import LeadCreate
from app.services.business_service import get_auto_reply_fallback
from app.utils.logger import logger

api_key = os.getenv("AI_API_KEY") or os.getenv("GROQ_API") or os.getenv("GROQ_API_KEY") or "missing_key"
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key,
    timeout=10.0,
)

MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPTS = {
    "SOLAR": """You are a professional assistant for a solar company.

Write a concise, warm email to a new lead.
Mention their solar consultation, a possible site visit, electricity bill savings, and that the team will follow up.
Do not overpromise savings, subsidies, pricing, or installation timelines.
Do not use markdown or bullet points.
Keep it under 160 words.""",
    "HOME_SERVICES": """You are a professional assistant for a home services company.

Write a concise, warm email to a new lead.
Mention their service request was received, the team will review the details, someone will follow up soon, and appointment/help can be arranged.
Do not use markdown or bullet points.
Keep it under 150 words.""",
    "OTHER_BUSINESS": """You are a professional email writer for the business described by the lead data.

Write the email that this business would send to its own customer or lead.
Use the business_type_text as the sender's business category and use automation_goal to understand what message the business owner wants to send.
Do not talk about automation services, workflow requests, demos, or an automation team.
If the business owner mentions an offer, benefit, follow-up, or service detail, include it naturally.
Do not use markdown or bullet points.
Keep it under 150 words.""",
}


def _lead_context(lead: LeadCreate) -> str:
    return f"""
lead name: {lead.full_name}
email: {lead.email}
phone: {lead.phone_number}
business type: {lead.business_type}
city: {lead.city or ""}
property type: {lead.property_type or ""}
monthly electricity bill: {lead.monthly_electricity_bill or ""}
extra fields: {lead.extra_fields or {}}
"""


def generate_email_sync(lead: LeadCreate) -> str:
    """Generate business-type-aware initial email with Groq."""
    if api_key == "missing_key":
        logger.warning("AI_API_KEY/GROQ_API is missing. Falling back to template.")
        raise ValueError("Groq API key not configured")

    prompt = SYSTEM_PROMPTS.get(lead.business_type, SYSTEM_PROMPTS["OTHER_BUSINESS"])

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": _lead_context(lead)},
            ],
            temperature=0.6,
            max_tokens=240,
        )
        generated_text = completion.choices[0].message.content.strip()
        logger.info(f"Successfully generated AI email for lead: {lead.email}")
        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate AI email: {e}")
        raise


def generate_auto_reply_sync(customer_message: str, business_type: str = "SOLAR") -> str:
    """Generate a short acknowledgment after a customer replies."""
    if api_key == "missing_key":
        logger.warning("AI_API_KEY/GROQ_API is missing. Falling back to template auto-reply.")
        return get_auto_reply_fallback(business_type)

    prompt = """You are a friendly business assistant.

Send a short acknowledgment email after a customer replies.
Maximum 2 sentences.
Do not answer detailed questions, negotiate, provide pricing, or book appointments.
Keep the wording appropriate to the business type."""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Business type: {business_type}\nCustomer reply: {customer_message}",
                },
            ],
            temperature=0.6,
            max_tokens=100,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to generate auto reply: {e}")
        return get_auto_reply_fallback(business_type)


async def generate_auto_reply(customer_message: str, business_type: str = "SOLAR") -> str:
    return generate_auto_reply_sync(customer_message, business_type)
