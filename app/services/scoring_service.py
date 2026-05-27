from app.schemas.lead import LeadCreate

def calculate_lead_score(lead: LeadCreate) -> tuple[int, str]:
    score = 0
    
    # Extract bill to integer (assuming it's a string like "12000" or similar, we'll try to convert)
    bill_amount = 0
    try:
        # Strip any non-numeric characters if needed, but assuming mostly clean input
        bill_str = ''.join(filter(str.isdigit, lead.monthly_electricity_bill))
        if bill_str:
            bill_amount = int(bill_str)
    except ValueError:
        pass
        
    # 1. Scoring Logic
    if lead.property_type.lower() == "commercial":
        score += 50
        
    if bill_amount >= 15000:
        score += 40
    elif bill_amount >= 7000:
        score += 25
        
    if lead.rooftop_size.lower() == "large":
        score += 30
    elif lead.rooftop_size.lower() == "medium":
        score += 15
        
    timeline_lower = lead.installation_timeline.lower()
    if "within 30 days" in timeline_lower or "immediately" in timeline_lower:
        score += 25
    elif "within 60 days" in timeline_lower:
        score += 10
        
    # 2. Category Logic
    category = "STANDARD"
    
    is_high_value = (
        lead.property_type.lower() == "commercial" or
        bill_amount >= 15000 or
        lead.rooftop_size.lower() == "large" or
        "within 30 days" in timeline_lower or
        "immediately" in timeline_lower
    )
    
    is_priority = (
        (7000 <= bill_amount < 15000 and lead.rooftop_size.lower() in ["medium", "large"]) or
        "within 60 days" in timeline_lower
    )
    
    if is_high_value:
        category = "HIGH_VALUE"
    elif is_priority:
        category = "PRIORITY"
        
    return score, category
