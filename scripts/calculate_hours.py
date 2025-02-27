import sys
from datetime import datetime, timedelta
import pytz
import requests
import json

def get_issue_id(issue_number, repo_owner, repo_name, token):
    """Fetches the issue ID from GitHub GraphQL API."""
    
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {token}",
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

    print(f"🔍 Debug: Fetching Issue ID for issue #{issue_number} from repo {repo_owner}/{repo_name}")

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch Issue ID. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)

    issue_data = response.json()
    print(f"🔍 Debug: Raw API Response: {json.dumps(issue_data, indent=2)}")

    issue_id = issue_data.get("data", {}).get("repository", {}).get("issue", {}).get("id", "")
    
    if not issue_id:
        print("❌ ERROR: Extracted issue_id is empty. Exiting script.")
        sys.exit(1)

    print(f"✅ Extracted ISSUE_ID: {issue_id}")
    return issue_id

if __name__ == "__main__":
    issue_number = sys.argv[1].strip()
    repo_owner = sys.argv[2]
    repo_name = sys.argv[3]
    project_id = sys.argv[4]
    priority = sys.argv[5]
    github_token = sys.argv[6]

    # Debugging: Print issue number received from workflow
    print(f"🔍 Debug: ISSUE_NUMBER received from workflow: '{issue_number}'")
    
    if not issue_number:
        print("❌ ERROR: issue_number is empty. Exiting script.")
        sys.exit(1)

    # Fetch correct issue ID using GitHub API
    issue_id = get_issue_id(issue_number, repo_owner, repo_name, github_token)
    
    print(f"✅ Using ISSUE_ID: {issue_id}")
    
    # Continue with the rest of the script
