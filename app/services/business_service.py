BUSINESS_LABELS = {
    "SOLAR": "Solar Company",
    "HOME_SERVICES": "Home Services",
    "OTHER_BUSINESS": "Other Business",
}

BOOKING_LABELS = {
    "SOLAR": "Book Site Visit",
    "HOME_SERVICES": "Book Service Appointment",
    "OTHER_BUSINESS": "Book Consultation",
}

INITIAL_SUBJECTS = {
    "SOLAR": "Thanks for Your Solar Inquiry",
    "HOME_SERVICES": "We Received Your Service Request",
    "OTHER_BUSINESS": "Thanks for Your Interest",
}

FOLLOW_UP_SUBJECTS = {
    "SOLAR": "Checking in on your solar inquiry",
    "HOME_SERVICES": "Checking in on your service request",
    "OTHER_BUSINESS": "Checking in on your automation request",
}


def normalize_business_type(value):
    if value in BUSINESS_LABELS:
        return value
    return "OTHER_BUSINESS"


def get_business_label(value):
    return BUSINESS_LABELS.get(normalize_business_type(value), "Other Business")


def get_booking_label(value):
    return BOOKING_LABELS.get(normalize_business_type(value), "Book Consultation")


def get_initial_subject(value):
    return INITIAL_SUBJECTS.get(normalize_business_type(value), INITIAL_SUBJECTS["OTHER_BUSINESS"])


def get_follow_up_subject(value):
    return FOLLOW_UP_SUBJECTS.get(normalize_business_type(value), FOLLOW_UP_SUBJECTS["OTHER_BUSINESS"])


def get_follow_up_body(lead, stage):
    if lead.business_type == "HOME_SERVICES":
        base = "Just checking if you still need help with your service request."
    elif lead.business_type == "OTHER_BUSINESS":
        base = "Just checking if you're still interested in automating this workflow."
    else:
        base = "Just checking if you're still interested in reducing your electricity bill or scheduling a solar consultation."

    if stage == 1:
        return f"Hi {lead.full_name}, {base}"
    if stage == 2:
        return f"Hi {lead.full_name}, following up once more. {base}"
    return f"Hi {lead.full_name}, this is our final quick check-in. {base}"


def _customer_facing_goal(goal):
    cleaned = (goal or "our services").strip()
    cleaned = cleaned.replace("follow ups", "follow-up messages")
    cleaned = cleaned.replace("benifits", "benefits")
    cleaned = cleaned.replace("tell them benefits", "share the benefits")
    cleaned = cleaned.replace("tell them that we give", "let them know we give")
    lower = cleaned.lower()
    for prefix in ("i want to ", "we want to ", "want to "):
        if lower.startswith(prefix):
            return f"We will follow up soon to {cleaned[len(prefix):].strip()}."
    return f"We will follow up soon with details about {cleaned}."


def get_fallback_initial_email(lead):
    if lead.business_type == "HOME_SERVICES":
        service = lead.extra_fields.get("service_needed", "your service request") if lead.extra_fields else "your service request"
        return f"""Hi {lead.full_name},

Thanks for reaching out. We received your request for {service}, and our team will review the details shortly.

Someone will follow up soon to understand what is needed and help arrange the next step or appointment.

Best regards,
The Team"""

    if lead.business_type == "OTHER_BUSINESS":
        business = lead.extra_fields.get("business_type_text", "your business") if lead.extra_fields else "your business"
        goal = lead.extra_fields.get("automation_goal", "our services") if lead.extra_fields else "our services"
        customer_message = _customer_facing_goal(goal)
        return f"""Hi {lead.full_name},

Thanks for your interest in our {business}. {customer_message}

Our team will contact you shortly and help you with the next step.

Best regards,
The Team"""

    return f"""Hi {lead.full_name},

Thanks for your interest in solar. We received your inquiry and our team will review your electricity bill, property details, and location.

We can discuss potential bill savings, whether a site visit makes sense, and the next practical step. We will follow up soon.

Best regards,
The Solar Team"""


def get_auto_reply_fallback(business_type):
    return "Thank you for your interest. Our team has received your message and will contact you shortly."
