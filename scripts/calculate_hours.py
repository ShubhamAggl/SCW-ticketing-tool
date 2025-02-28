import sys
from datetime import datetime, timedelta
import pytz
import requests
import json

# GitHub API Headers
def get_github_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

# Function to Fetch Issue Events (Status Changes)
def get_issue_status_changes(issue_number, repo_owner, repo_name, token):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/events"
    
    response = requests.get(url, headers=get_github_headers(token))

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch issue events. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return []

    return response.json()

# Adjust Timestamp to Business Hours (IST)
def adjust_to_business_hours(dt):
    ist = pytz.timezone('Asia/Kolkata')
    dt = dt.astimezone(ist)

    # Business Hours: 10 AM - 6 PM IST (Monday - Friday)
    if dt.weekday() >= 5:  # Skip weekends
        days_to_monday = 7 - dt.weekday()
        dt = dt.replace(hour=10, minute=0, second=0) + timedelta(days=days_to_monday)

    if dt.hour < 10:  # Before 10 AM, move to 10 AM
        dt = dt.replace(hour=10, minute=0, second=0)
    elif dt.hour >= 18:  # After 6 PM, move to next day 10 AM
        dt = dt.replace(hour=10, minute=0, second=0) + timedelta(days=1)
        while dt.weekday() >= 5:
            dt += timedelta(days=1)

    return dt

# Calculate Business Hours in SLA-relevant Statuses
def calculate_sla_time(issue_events):
    sla_statuses = {"Triage", "In-Progress", "Resolved"}
    paused_statuses = {"Dependent on Customer"}
    ignored_statuses = {"Enhancement", "Cancelled"}

    ist = pytz.timezone('Asia/Kolkata')
    total_seconds = 0
    active_start = None

    print("🔍 Debug: Tracking SLA Status Changes from Issue Events")

    for event in issue_events:
        if event["event"] not in ["labeled", "unlabeled"]:
            continue  # Only process status changes

        status = event.get("label", {}).get("name", "")
        timestamp = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00")).astimezone(ist)

        print(f"🕒 Status Change: {status} at {timestamp}")

        if status in sla_statuses:
            if active_start is None:
                active_start = adjust_to_business_hours(timestamp)
                print(f"✅ SLA Started at {active_start}")
        elif status in paused_statuses and active_start:
            total_seconds += (timestamp - active_start).total_seconds()
            print(f"⏸️ SLA Paused, Time Counted: {total_seconds} seconds")
            active_start = None
        elif status in ignored_statuses:
            print("❌ Ignored Status - Stopping SLA Calculation")
            active_start = None

    if active_start:
        total_seconds += (datetime.now(ist) - active_start).total_seconds()

    print(f"⏳ Total SLA Business Seconds: {total_seconds}")

    return int(total_seconds)

# SLA Threshold Mapping Based on Priority
def get_sla_threshold(priority):
    sla_mapping = {
        "P1": 16 * 3600,  # 2 days * 8 business hours in seconds
        "P2": 24 * 3600,  # 3 days * 8 business hours in seconds
        "P3": 32 * 3600,  # 4 days * 8 business hours in seconds
        "P4": 40 * 3600,  # 5 days * 8 business hours in seconds
    }
    return sla_mapping.get(priority, 40 * 3600)

# Convert Total Seconds to HH:MM:SS Format
def format_seconds_to_hms(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"

def get_issue_id(repo_owner, repo_name, github_token):
    """Fetches the issue ID from GitHub API when issue_number is missing."""
    
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues?state=all&per_page=1"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
    
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch issue ID. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None

    issue_data = response.json()
    
    if not issue_data or "number" not in issue_data[0]:
        print("❌ ERROR: No valid issue data found.")
        return None
    
    return str(issue_data[0]["number"])  # Convert issue number to string

# Main Execution
if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("❌ ERROR: Missing arguments. Usage: calculate_hours.py <issue_number> <repo_owner> <repo_name> <github_token>")
        sys.exit(1)

    issue_number = sys.argv[1].strip()
    repo_owner = sys.argv[2].strip()
    repo_name = sys.argv[3].strip()
    github_token = sys.argv[4].strip()

    print(f"🔍 Debug: ISSUE_NUMBER received in Python script: '{issue_number}'")

    # 🔥 Fix: Fetch issue number if it's empty
    if not issue_number or issue_number == "''":
        print("⚠️ WARNING: issue_number is empty! Fetching from GitHub...")
        issue_number = get_issue_id(repo_owner, repo_name, github_token)

    if not issue_number:
        print("❌ ERROR: Unable to retrieve a valid issue number. Exiting.")
        sys.exit(1)

    print(f"✅ Using ISSUE_NUMBER: {issue_number}")

    issue_events = get_issue_status_changes(issue_number, repo_owner, repo_name, github_token)
    
    if not issue_events:
        print("❌ ERROR: No issue events found. Exiting.")
        sys.exit(1)
    total_business_seconds = calculate_sla_time(issue_events)
    formatted_time = format_seconds_to_hms(total_business_seconds)

    priority = "P4"  # Default Priority if not provided
    sla_threshold = get_sla_threshold(priority)

    sla_breached = "Breached" if total_business_seconds > sla_threshold else "WithinSLA"

    print(f"Total Hours (Seconds): {total_business_seconds}")  # Store total business hours in seconds
    print(f"SLA Breached: {sla_breached}")
