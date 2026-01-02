#!/usr/bin/env python3
"""
AI Code Reviewer Script

This script reviews code changes in a pull request using OpenAI's ChatGPT API
and posts review comments on the PR.
"""

import argparse
import os
import sys
from pathlib import Path

import requests
from openai import OpenAI


def get_env_var(name: str) -> str:
    """Get required environment variable or exit with error."""
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable is required")
        sys.exit(1)
    return value


def load_system_prompt(prompt_file: str) -> str:
    """Load the system prompt from the specified file."""
    prompt_path = Path(prompt_file)
    
    if not prompt_path.exists():
        print(f"Warning: System prompt file '{prompt_file}' not found. Using default prompt.")
        return get_default_system_prompt()
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def get_default_system_prompt() -> str:
    """Return a default system prompt if no custom prompt is found."""
    return """You are an expert code reviewer with deep knowledge of software engineering best practices.

Your role is to review code changes and provide constructive, actionable feedback.

## Review Guidelines

1. **Code Quality**: Check for clean code principles, readability, and maintainability
2. **Bugs & Errors**: Identify potential bugs, edge cases, and error handling issues
3. **Security**: Flag security vulnerabilities and suggest fixes
4. **Performance**: Identify performance bottlenecks and optimization opportunities
5. **Best Practices**: Suggest improvements based on language-specific best practices

## Feedback Format

For each issue found, provide:
- **Location**: File and line number (if applicable)
- **Issue**: Clear description of the problem
- **Suggestion**: Concrete recommendation for improvement
- **Severity**: LOW, MEDIUM, HIGH, or CRITICAL

Be constructive, specific, and focus on the most impactful issues first.
"""


def get_file_diff(repo_owner: str, repo_name: str, pr_number: int, github_token: str) -> dict:
    """Get the diff for all files in the PR."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3.diff'
    }
    
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching PR diff: {response.status_code}")
        return ""
    
    return response.text


def get_file_contents(repo_owner: str, repo_name: str, file_path: str, ref: str, github_token: str) -> str:
    """Get the contents of a file at a specific ref."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3.raw'
    }
    
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}?ref={ref}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return ""
    
    return response.text


def get_pr_details(repo_owner: str, repo_name: str, pr_number: int, github_token: str) -> dict:
    """Get PR details including head SHA."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching PR details: {response.status_code}")
        return {}
    
    return response.json()


def review_code_with_ai(client: OpenAI, system_prompt: str, file_name: str, diff_content: str, file_content: str) -> str:
    """Use ChatGPT to review the code changes."""
    user_prompt = f"""Please review the following code changes:

## File: {file_name}

### Diff:
```
{diff_content}
```

### Full File Content (for context):
```
{file_content[:10000]}  # Truncate to avoid token limits
```

Provide your code review following the guidelines in your system prompt.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return ""


def post_review_comment(repo_owner: str, repo_name: str, pr_number: int, comment: str, github_token: str) -> bool:
    """Post a review comment on the PR."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments'
    data = {'body': comment}
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 201:
        print(f"Error posting comment: {response.status_code} - {response.text}")
        return False
    
    return True


def parse_changed_files(files_str: str) -> list:
    """Parse the changed files string into a list."""
    if not files_str:
        return []
    return [f.strip() for f in files_str.split() if f.strip()]


def main():
    parser = argparse.ArgumentParser(description='AI Code Reviewer')
    parser.add_argument('--files', type=str, required=True, help='Space-separated list of changed files')
    args = parser.parse_args()
    
    # Get environment variables
    github_token = get_env_var('GITHUB_TOKEN')
    openai_api_key = get_env_var('OPENAI_API_KEY')
    system_prompt_file = os.environ.get('SYSTEM_PROMPT_FILE', '.github/prompts/system_prompt.md')
    pr_number = int(get_env_var('PR_NUMBER'))
    repo_owner = get_env_var('REPO_OWNER')
    repo_name = get_env_var('REPO_NAME')
    
    # Initialize OpenAI client
    client = OpenAI(api_key=openai_api_key)
    
    # Load system prompt
    system_prompt = load_system_prompt(system_prompt_file)
    print(f"Loaded system prompt from: {system_prompt_file}")
    
    # Get changed files
    changed_files = parse_changed_files(args.files)
    if not changed_files:
        print("No changed files to review")
        return
    
    print(f"Reviewing {len(changed_files)} file(s)...")
    
    # Get PR details
    pr_details = get_pr_details(repo_owner, repo_name, pr_number, github_token)
    if not pr_details:
        print("Failed to get PR details")
        sys.exit(1)
    
    head_sha = pr_details.get('head', {}).get('sha', '')
    
    # Get the full diff
    diff_content = get_file_diff(repo_owner, repo_name, pr_number, github_token)
    
    # Review each file
    all_reviews = []
    for file_path in changed_files:
        print(f"Reviewing: {file_path}")
        
        # Get file content
        file_content = get_file_contents(repo_owner, repo_name, file_path, head_sha, github_token)
        
        # Extract file-specific diff (simplified - uses full diff for context)
        file_diff = ""
        in_file_diff = False
        for line in diff_content.split('\n'):
            if line.startswith('diff --git') and file_path in line:
                in_file_diff = True
                file_diff = line + '\n'
            elif line.startswith('diff --git') and in_file_diff:
                break
            elif in_file_diff:
                file_diff += line + '\n'
        
        if not file_diff:
            file_diff = f"File changed: {file_path}\n(Full diff not available)"
        
        # Get AI review
        review = review_code_with_ai(client, system_prompt, file_path, file_diff, file_content)
        if review:
            all_reviews.append(f"## 📝 Review for `{file_path}`\n\n{review}")
    
    # Post consolidated review
    if all_reviews:
        full_review = "# 🤖 AI Code Review\n\n" + "\n\n---\n\n".join(all_reviews)
        full_review += "\n\n---\n*This review was automatically generated by the AI Code Review Agent.*"
        
        if post_review_comment(repo_owner, repo_name, pr_number, full_review, github_token):
            print("Successfully posted code review")
        else:
            print("Failed to post code review")
            sys.exit(1)
    else:
        print("No reviews generated")


if __name__ == '__main__':
    main()

