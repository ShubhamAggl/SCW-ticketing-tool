import sys
from datetime import datetime, timedelta
import pytz
import requests
import json

def get_issue_status_changes(issue_number, repo_owner, repo_name, project_id, token):
    """Fetches the status change history of an issue from GitHub Projects API."""
    
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    
    query = """
    query($projectId: ID!, $issueNumber: Int!) {
      repository(owner: "%s", name: "%s") {
        issue(number: $issueNumber) {
          projectItems(first: 10) {
            nodes {
              fieldValues(first: 10) {
                nodes {
                  ... on ProjectV2ItemFieldTextValue {
                    text
                  }
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                  }
                  updatedAt
                }
              }
            }
          }
        }
      }
    }
    """ % (repo_owner, repo_name)

    payload = {
        "query": query,
        "variables": {
            "projectId": project_id,
            "issueNumber": int(issue_number)
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch project issue events. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return []

    return response.json()


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

def calculate_sla_time(issue_events):
    """Calculates the total business hours spent on SLA-relevant statuses."""
    sla_statuses = {"Triage", "In-Progress", "Resolved"}
    paused_statuses = {"Dependent on Customer"}
    ignored_statuses = {"Enhancement", "Cancelled"}

    ist = pytz.timezone('Asia/Kolkata')
    total_seconds = 0
    active_start = None

    print("🔍 Debug: Tracking SLA Status Changes from Project Fields")

    for event in issue_events.get("data", {}).get("repository", {}).get("issue", {}).get("projectItems", {}).get("nodes", []):
        for field in event.get("fieldValues", {}).get("nodes", []):
            if "text" in field:
                status = field["text"]
            elif "name" in field:
                status = field["name"]
            else:
                continue

            timestamp = datetime.fromisoformat(field["updatedAt"].replace('Z', '+00:00')).astimezone(ist)

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

def get_sla_threshold(priority):
    """Returns the SLA threshold in business hours based on priority label."""
    sla_mapping = {
        "P1": 16 * 3600,  # 2 days * 8 business hours in seconds
        "P2": 24 * 3600,  # 3 days * 8 business hours in seconds
        "P3": 32 * 3600,  # 4 days * 8 business hours in seconds
        "P4": 40 * 3600,  # 5 days * 8 business hours in seconds
    }
    return sla_mapping.get(priority, 40 * 3600)

if __name__ == "__main__":
    issue_number = sys.argv[1]
    repo_owner = sys.argv[2]
    repo_name = sys.argv[3]
    project_id = sys.argv[4]  # Missing project_id added
    priority = sys.argv[5]
    github_token = sys.argv[6]  # Ensure we pass the GitHub token correctly

    # ✅ Correctly indented lines
    issue_events = get_issue_status_changes(issue_number, repo_owner, repo_name, project_id, github_token)
    total_business_seconds = calculate_sla_time(issue_events)
    sla_threshold = get_sla_threshold(priority)
    
    sla_breached = "Breached" if total_business_seconds > sla_threshold else "WithinSLA"
    
    print(f"Total Hours (Seconds): {total_business_seconds}")  # Store total business hours in seconds
    print(f"SLA Breached: {sla_breached}")
