from typing import Optional
from app.schemas.lead import LeadCreate


def _digits_to_int(value: Optional[str]) -> int:
    if not value:
        return 0
    digits = "".join(filter(str.isdigit, str(value)))
    return int(digits) if digits else 0


def _text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def calculate_lead_score(lead: LeadCreate) -> tuple[int, str]:
    business_type = lead.business_type

    if business_type == "HOME_SERVICES":
        urgency = _text(lead.extra_fields.get("urgency"))
        if any(word in urgency for word in ["urgent", "emergency", "today", "asap"]):
            return 90, "HIGH_VALUE"
        if any(word in urgency for word in ["soon", "this week", "week"]):
            return 65, "PRIORITY"
        return 35, "STANDARD"

    if business_type == "OTHER_BUSINESS":
        goal = _text(lead.extra_fields.get("automation_goal"))
        if any(word in goal for word in ["urgent", "revenue", "lead", "sales", "customer", "lost"]):
            return 85, "HIGH_VALUE"
        if len(goal) >= 24:
            return 60, "PRIORITY"
        return 30, "STANDARD"

    bill_amount = _digits_to_int(lead.monthly_electricity_bill)
    property_type = _text(lead.property_type)

    if property_type == "commercial" or bill_amount >= 15000:
        return 90, "HIGH_VALUE"
    if bill_amount >= 7000 or property_type in ["residential", "industrial"]:
        return 60, "PRIORITY"
    return 35, "STANDARD"
