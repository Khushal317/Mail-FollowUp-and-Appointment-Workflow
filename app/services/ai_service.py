import os
from openai import OpenAI
from app.schemas.lead import LeadCreate
from app.utils.logger import logger

# Initialize synchronous OpenAI client with NVIDIA base URL
api_key = os.getenv("NVIDIA_API_KEY", "missing_key")
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key,
    timeout=10.0
)

SYSTEM_PROMPT = """You are a professional solar sales assistant for a modern solar installation company.

Your task is to write a highly personalized and professional email response to a new solar lead.

The email should:
thank the lead for submitting the inquiry
sound warm and human
reference their city and property type naturally
mention potential electricity savings
ask follow-up qualification questions
encourage replying to the email
sound concise and professional
avoid sounding robotic or overly salesy

The follow-up questions should include:
approximate rooftop size
average daytime electricity usage
preferred installation timeline

Keep the email under 180 words.

Do NOT use markdown.
Do NOT use bullet points.
Write in natural conversational email format.
"""

def generate_email_sync(lead: LeadCreate) -> str:
    """Synchronous AI email generation. Works in both FastAPI and Celery contexts."""
    if api_key == "missing_key":
        logger.warning("NVIDIA_API_KEY is missing. Falling back to template.")
        raise ValueError("NVIDIA_API_KEY not configured")

    user_context = f"""
lead name: {lead.full_name}
city: {lead.city}
property type: {lead.property_type}
electricity bill: {lead.monthly_electricity_bill}
timeline: {lead.installation_timeline}
"""

    try:
        completion = client.chat.completions.create(
            model="meta/llama3-70b-instruct",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_context}
            ],
            temperature=0.7,
            max_tokens=256
        )
        generated_text = completion.choices[0].message.content.strip()
        logger.info(f"Successfully generated AI email for lead: {lead.email}")
        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate AI email: {e}")
        raise e

AUTO_REPLY_PROMPT = """You are a friendly solar company assistant.

Your task is ONLY to send a short acknowledgment email after a customer replies.

Rules:
maximum 2 sentences
friendly and human
acknowledge their message naturally
tell them a solar specialist will contact them shortly
do not answer detailed questions
do not negotiate
do not provide pricing
do not book appointments
do not sound robotic"""

def generate_auto_reply_sync(customer_message: str) -> str:
    """Synchronous auto-reply generation."""
    if api_key == "missing_key":
        logger.warning("NVIDIA_API_KEY is missing. Falling back to template auto-reply.")
        return "Thanks for your reply! One of our solar specialists will contact you shortly to assist further."

    try:
        completion = client.chat.completions.create(
            model="meta/llama3-70b-instruct",
            messages=[
                {"role": "system", "content": AUTO_REPLY_PROMPT},
                {"role": "user", "content": f"Customer reply: '{customer_message}'"}
            ],
            temperature=0.7,
            max_tokens=100
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to generate auto reply: {e}")
        return "Thanks for your reply! One of our solar specialists will contact you shortly to assist further."
