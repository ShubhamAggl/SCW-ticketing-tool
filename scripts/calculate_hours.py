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
            "issueNumber": int(issue_number) if issue_number.isdigit() else None
        }
    }

    if not issue_number or not issue_number.strip():
        print("❌ ERROR: issue_number is empty. Creating a new issue...")
        return create_new_issue(repo_owner, repo_name, token)

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch project issue events. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return []

    return response.json()

def create_new_issue(repo_owner, repo_name, token):
    """Creates a new issue when issue_number is not found."""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    payload = {
        "title": "Auto-generated issue",
        "body": "This issue was automatically created because the original issue number was not found.",
        "labels": ["auto-generated"]
    }
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 201:
        print(f"❌ Failed to create a new issue. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)
    
    issue_data = response.json()
    new_issue_number = issue_data.get("number")
    print(f"✅ Successfully created issue #{new_issue_number}")
    return new_issue_number

if __name__ == "__main__":
    issue_number = sys.argv[1]
    repo_owner = sys.argv[2]
    repo_name = sys.argv[3]
    project_id = sys.argv[4]  # Missing project_id added
    priority = sys.argv[5]
    github_token = sys.argv[6]  # Ensure we pass the GitHub token correctly

    issue_events = get_issue_status_changes(issue_number, repo_owner, repo_name, project_id, github_token)
    if isinstance(issue_events, int):  # If a new issue number was returned
        issue_number = str(issue_events)
        issue_events = get_issue_status_changes(issue_number, repo_owner, repo_name, project_id, github_token)
    
    total_business_seconds = calculate_sla_time(issue_events)
    sla_threshold = get_sla_threshold(priority)
    
    sla_breached = "Breached" if total_business_seconds > sla_threshold else "WithinSLA"
    
    print(f"Total Hours (Seconds): {total_business_seconds}")  # Store total business hours in seconds
    print(f"SLA Breached: {sla_breached}")
