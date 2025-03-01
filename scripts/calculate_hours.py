import sys
from datetime import datetime, timedelta
import pytz
import json

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

def calculate_business_hours(active_periods):
    """Calculates business hours only within active SLA periods."""
    ist = pytz.timezone('Asia/Kolkata')
    business_seconds = 0
    
    for period in active_periods:
        start_time = adjust_to_business_hours(datetime.fromisoformat(period['start']).astimezone(pytz.utc))
        end_time = adjust_to_business_hours(datetime.fromisoformat(period['end']).astimezone(pytz.utc))
        
        current_time = start_time
        while current_time < end_time:
            if current_time.weekday() < 5 and 10 <= current_time.hour < 18:
                business_seconds += 1
            current_time += timedelta(seconds=1)
    
    return business_seconds

def get_sla_threshold(priority):
    """Returns the SLA threshold in business hours based on priority label."""
    sla_mapping = {
        "P1": 30,  # ⚡ Testing: 30 seconds instead of 16 hours
        "P2": 60,  # 3 days * 8 business hours in seconds
        "P3": 120,  # 4 days * 8 business hours in seconds
        "P4": 200,  # 5 days * 8 business hours in seconds
    }
    return sla_mapping.get(priority, 40 * 3600)

if __name__ == "__main__":
    active_periods_json = sys.argv[1]
    priority = sys.argv[2].strip()
    
    active_periods = json.loads(active_periods_json)
    total_business_seconds = calculate_business_hours(active_periods)
    sla_threshold = get_sla_threshold(priority)
    
    # Debugging Output
    print(f"Priority Received: '{priority}'")
    print(f"Total Business Seconds: {total_business_seconds}")
    print(f"SLA Threshold (Seconds): {sla_threshold}")
    
    # Ensure comparison in seconds
    sla_breached = "Breached" if total_business_seconds > sla_threshold else "WithinSLA"
    
    print(f"Total Hours: {total_business_seconds}")  # Store total business hours in seconds
    print(f"SLA Breached: {sla_breached}")
