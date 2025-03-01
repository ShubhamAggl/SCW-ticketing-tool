import sys
import requests
import json
from datetime import datetime, timedelta
import pytz

def get_issue_details(issue_id, github_token):
    """
    Fetches issue metadata, including createdAt, closedAt, and labels.
    """
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
    query = """
    query($issueId: ID!) {
      node(id: $issueId) {
        ... on Issue {
          createdAt
          closedAt
          labels(first: 10) {
            nodes { name }
          }
        }
      }
    }
    """
    variables = {"issueId": issue_id}

    response = requests.post(url, headers=headers, json={"query": query, "variables": variables})

    # Debugging: Print response status and body
    print(f"🔍 Debug: GitHub API Response Status: {response.status_code}")
    print(f"🔍 Debug: GitHub API Response Body: {response.text}")

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch issue details. Status Code: {response.status_code}")
        return None

    response_json = response.json()
    
    if "message" in response_json:
        print(f"❌ ERROR from GitHub: {response_json['message']}")
        sys.exit(1)

    if "data" not in response_json or not response_json["data"].get("node"):
        print("❌ ERROR: 'data' key missing in API response!")
        return None

    return response_json.get("data", {}).get("node", {})

def calculate_business_hours(start_time, end_time):
    """
    Calculate total business hours (9 AM - 6 PM IST) between start_time and end_time.
    Excludes weekends.
    Returns total time in seconds.
    """
    ist = pytz.timezone('Asia/Kolkata')
    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(ist)
    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00')).astimezone(ist)
    
    business_start = 9  # 9 AM IST
    business_end = 18  # 6 PM IST
    
    total_seconds = 0
    current_time = start_time
    
    while current_time < end_time:
        if current_time.weekday() < 5:  # Monday to Friday
            if business_start <= current_time.hour < business_end:
                remaining_seconds_today = min((end_time - current_time).total_seconds(), (business_end - current_time.hour) * 3600)
                total_seconds += remaining_seconds_today
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=business_start, minute=0, second=0)
        else:
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=business_start, minute=0, second=0)
    
    return int(total_seconds)

def get_sla_threshold(priority):
    """
    Returns the SLA threshold in seconds based on priority label.
    """
    sla_mapping = {
        "P1": 30,   # ⚡ Testing: 30 seconds instead of 16 hours
        "P2": 60,   # Testing
        "P3": 120,  # Testing
        "P4": 200   # Testing
    }
    return sla_mapping.get(priority, 200)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("❌ ERROR: Missing arguments. Usage: calculate_hours.py <start_time> <end_time> <priority>")
        sys.exit(1)

    start_time, end_time, priority = sys.argv[1:4]

    print(f"🔍 Debug: Received Inputs - Start Time: {start_time}, End Time: {end_time}, Priority: {priority}")

    try:
        total_business_seconds = calculate_business_hours(start_time, end_time)
        sla_threshold = get_sla_threshold(priority)
        sla_breached = "Breached" if total_business_seconds > sla_threshold else "WithinSLA"

        print(f"Total Hours: {total_business_seconds}")  # ✅ Output only the number
        print(f"SLA Breached: {sla_breached}")

    except Exception as e:
        print(f"❌ ERROR: Exception occurred in the script: {e}")
        sys.exit(1)
