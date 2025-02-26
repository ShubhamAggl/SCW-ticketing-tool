import sys
from datetime import datetime, timedelta
import pytz

def adjust_to_business_hours(dt):
    """Adjusts the timestamp to the nearest business hour boundary in IST."""
    ist = pytz.timezone('Asia/Kolkata')
    dt = dt.astimezone(ist)
    
    # Business hours: 10 AM - 6 PM IST (Monday-Friday)
    if dt.weekday() >= 5:  # Weekend (Saturday-Sunday)
        days_to_monday = 7 - dt.weekday()
        dt = dt.replace(hour=10, minute=0, second=0) + timedelta(days=days_to_monday)
    elif dt.hour < 10:
        dt = dt.replace(hour=10, minute=0, second=0)
    elif dt.hour >= 18:
        dt = dt.replace(hour=10, minute=0, second=0) + timedelta(days=1)
        while dt.weekday() >= 5:  # Skip weekends
            dt += timedelta(days=1)
    
    return dt

def calculate_business_hours(start_time, end_time):
    """Calculates business hours between two datetime objects."""
    ist = pytz.timezone('Asia/Kolkata')
    start_time = adjust_to_business_hours(start_time)
    end_time = adjust_to_business_hours(end_time)
    
    business_hours = 0
    current_time = start_time
    
    while current_time < end_time:
        if current_time.weekday() < 5 and 10 <= current_time.hour < 18:
            business_hours += 1
        current_time += timedelta(hours=1)
    
    return business_hours

def get_sla_threshold(priority):
    """Returns the SLA threshold in business hours based on priority label."""
    sla_mapping = {
        "P1": 16,  # 2 days * 8 business hours
        "P2": 24,  # 3 days * 8 business hours
        "P3": 32,  # 4 days * 8 business hours
        "P4": 40,  # 5 days * 8 business hours
    }
    return sla_mapping.get(priority, 40)

if __name__ == "__main__":
    start_time = datetime.fromisoformat(sys.argv[1].replace('Z', '+00:00')).astimezone(pytz.utc)
    end_time = datetime.fromisoformat(sys.argv[2].replace('Z', '+00:00')).astimezone(pytz.utc)
    priority = sys.argv[3]
    
    total_business_hours = calculate_business_hours(start_time, end_time)
    sla_threshold = get_sla_threshold(priority)
    sla_breached = "Breached" if total_business_hours > sla_threshold else "Within SLA"
    
    print(f"Total Hours: {total_business_hours}")
    print(f"SLA Breached: {sla_breached}")
