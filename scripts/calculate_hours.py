import sys
import requests
import json
from datetime import datetime
import pytz

def get_project_item_status_changes(issue_number, repo_owner, repo_name, project_id, github_token):
    """
    Fetches the status change history of an issue from GitHub Projects API (ProjectV2).
    """

    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }

    query = """
    query($repoOwner: String!, $repoName: String!, $issueNumber: Int!, $projectId: ID!) {
      repository(owner: $repoOwner, name: $repoName) {
        issue(number: $issueNumber) {
          projectItems(first: 10) {
            nodes {
              fieldValues(first: 10) {
                nodes {
                  ... on ProjectV2ItemFieldTextValue {
                    text
                    updatedAt
                  }
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    updatedAt
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    variables = {
        "repoOwner": repo_owner,
        "repoName": repo_name,
        "issueNumber": int(issue_number),
        "projectId": project_id
    }

    response = requests.post(url, headers=headers, json={"query": query, "variables": variables})

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch issue status changes. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return []

    try:
        data = response.json()
        return data.get("data", {}).get("repository", {}).get("issue", {}).get("projectItems", {}).get("nodes", [])
    except json.JSONDecodeError:
        print("❌ ERROR: Failed to parse JSON response.")
        return []

def calculate_business_hours(status_events):
    """
    Calculates total business hours spent on SLA-relevant statuses (Triage, In-Progress, Resolved).
    """

    sla_statuses = {"Triage", "In-Progress", "Resolved"}
    paused_statuses = {"Dependent on Customer"}
    ignored_statuses = {"Enhancement", "Cancelled"}

    ist = pytz.timezone('Asia/Kolkata')
    total_seconds = 0
    active_start = None

    print("🔍 Debug: Tracking SLA Status Changes from Project Fields")

    for event in status_events:
        for field in event.get("fieldValues", {}).get("nodes", []):
            status = field.get("text") or field.get("name")
            timestamp = datetime.fromisoformat(field["updatedAt"].replace('Z', '+00:00')).astimezone(ist)

            print(f"🕒 Status Change: {status} at {timestamp}")

            if status in sla_statuses:
                if active_start is None:
                    active_start = timestamp
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
    """
    Returns the SLA threshold in business hours based on priority label.
    """
    sla_mapping = {
        "P1": 16 * 3600,  # 2 days * 8 business hours in seconds
        "P2": 24 * 3600,  # 3 days * 8 business hours in seconds
        "P3": 32 * 3600,  # 4 days * 8 business hours in seconds
        "P4": 40 * 3600,  # 5 days * 8 business hours in seconds
    }
    return sla_mapping.get(priority, 40 * 3600)

# Main Execution
if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("❌ ERROR: Missing arguments. Usage: calculate_hours.py <issue_number> <repo_owner> <repo_name> <project_id> <github_token>")
        sys.exit(1)

    issue_number = sys.argv[1].strip()
    repo_owner = sys.argv[2].strip()
    repo_name = sys.argv[3].strip()
    project_id = sys.argv[4].strip()
    github_token = sys.argv[5].strip()

    print(f"🔍 Debug: ISSUE_NUMBER received in Python script: '{issue_number}'")
    print(f"🔍 Debug: GH_TOKEN Length in Python: {len(github_token)}")

    if not issue_number or issue_number in ["''", "None"]:
        print("❌ ERROR: issue_number is empty! Exiting.")
        sys.exit(1)

    status_events = get_project_item_status_changes(issue_number, repo_owner, repo_name, project_id, github_token)

    if not status_events:
        print("❌ ERROR: No status change events found for the issue. Exiting.")
        sys.exit(1)

    total_business_seconds = calculate_business_hours(status_events)
    sla_threshold = get_sla_threshold("P1")  # Adjust to match the issue's priority

    sla_breached = "Breached" if total_business_seconds > sla_threshold else "WithinSLA"

    print(f"Total Hours (Seconds): {total_business_seconds}")  # Store total business hours in seconds
    print(f"SLA Breached: {sla_breached}")
