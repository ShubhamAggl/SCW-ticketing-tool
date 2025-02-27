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
        print("❌ ERROR: issue_number is empty. Exiting script.")
        sys.exit(1)

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch project issue events. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return []

    return response.json()

if __name__ == "__main__":
    issue_number = sys.argv[1]
    repo_owner = sys.argv[2]
    repo_name = sys.argv[3]
    project_id = sys.argv[4]  # Missing project_id added
    priority = sys.argv[5]
    github_token = sys.argv[6]  # Ensure we pass the GitHub token correctly

    # Fetch Issue ID correctly using GitHub API
    url = f"https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
    query = """
    query($repoOwner: String!, $repoName: String!, $issueNumber: Int!) {
      repository(owner: $repoOwner, name: $repoName) {
        issue(number: $issueNumber) {
          id
        }
      }
    }
    """
    payload = {
        "query": query,
        "variables": {
            "repoOwner": repo_owner,
            "repoName": repo_name,
            "issueNumber": int(issue_number)
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch Issue ID. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)

    issue_data = response.json()
    issue_number = issue_data.get("data", {}).get("repository", {}).get("issue", {}).get("id", "")
    
    print(f"🔍 Debug: Extracted ISSUE_NUMBER: '{issue_number}'")
    
    if not issue_number or not issue_number.strip():
        print("❌ ERROR: Extracted issue_number is empty. Exiting script.")
        sys.exit(1)

    issue_events = get_issue_status_changes(issue_number, repo_owner, repo_name, project_id, github_token)
    total_business_seconds = calculate_sla_time(issue_events)
    sla_threshold = get_sla_threshold(priority)
    
    sla_breached = "Breached" if total_business_seconds > sla_threshold else "WithinSLA"
    
    print(f"Total Hours (Seconds): {total_business_seconds}")  # Store total business hours in seconds
    print(f"SLA Breached: {sla_breached}")
