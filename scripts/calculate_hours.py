import sys
import requests
import json
from datetime import datetime, timedelta
import pytz

def get_issue_details(issue_number, repo_owner, repo_name, github_token):
    """
    Fetches issue metadata, including createdAt, closedAt, and labels.
    """
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
    query = """
    query($repoOwner: String!, $repoName: String!, $issueNumber: Int!) {
      repository(owner: $repoOwner, name: $repoName) {
        issue(number: $issueNumber) {
          createdAt
          closedAt
          labels(first: 10) {
            nodes { name }
          }
        }
      }
    }
    """
    variables = {"repoOwner": repo_owner, "repoName": repo_name, "issueNumber": int(issue_number)}
    response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
    
    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch issue details. Status Code: {response.status_code}")
        return None
    
    return response.json().get("data", {}).get("repository", {}).get("issue", {})

def calculate_business_hours(start_time, end_time):
    """
    Calculate total business hours (9 AM - 6 PM IST) between start_time and end_time.
    Excludes weekends.
    """
    ist = pytz.timezone('Asia/Kolkata')
    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(ist)
    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00')).astimezone(ist)
    
    business_start = 9  # 9 AM IST
    business_end = 18  # 6 PM IST
    
    total_hours = 0
    current_time = start_time
    
    while current_time < end_time:
        if current_time.weekday() < 5:  # Monday to Friday
            if business_start <= current_time.hour < business_end:
                remaining_hours_today = min((end_time - current_time).total_seconds() / 3600, business_end - current_time.hour)
                total_hours += remaining_hours_today
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=business_start, minute=0, second=0)
        else:
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=business_start, minute=0, second=0)
    
    return round(total_hours, 2)

def get_sla_threshold(priority):
    """
    Returns the SLA threshold in business hours based on priority label.
    """
    sla_mapping = {"P1": 16, "P2": 24, "P3": 32, "P4": 40}  # Hours
    return sla_mapping.get(priority, 40)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("❌ ERROR: Missing arguments. Usage: calculate_hours.py <issue_number> <repo_owner> <repo_name> <github_token>")
        sys.exit(1)
    
    issue_number, repo_owner, repo_name, github_token = sys.argv[1:5]
    issue_data = get_issue_details(issue_number, repo_owner, repo_name, github_token)
    
    if not issue_data or not issue_data.get("createdAt") or not issue_data.get("closedAt"):
        print("❌ ERROR: Missing issue timestamps. Exiting.")
        sys.exit(1)
    
    priority_labels = [label["name"] for label in issue_data.get("labels", {}).get("nodes", []) if label["name"] in ["P1", "P2", "P3", "P4"]]
    priority = priority_labels[0] if priority_labels else "P4"
    
    total_business_hours = calculate_business_hours(issue_data["createdAt"], issue_data["closedAt"])
    sla_threshold = get_sla_threshold(priority)
    sla_breached = "Breached" if total_business_hours > sla_threshold else "WithinSLA"
    
    print(f"Total Business Hours: {total_business_hours}")
    print(f"SLA Breached: {sla_breached}")
