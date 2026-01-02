#!/usr/bin/env python3
"""
System Prompt Updater Script

This script analyzes human review comments from a merged PR and updates
the system prompt to incorporate recurring feedback patterns.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import requests
from openai import OpenAI


def get_env_var(name: str) -> str:
    """Get required environment variable or exit with error."""
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable is required")
        sys.exit(1)
    return value


def get_review_comments(repo_owner: str, repo_name: str, pr_number: int, github_token: str) -> list:
    """Fetch all review comments from the PR."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    comments = []
    
    # Get PR review comments (inline comments on code)
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/comments'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        for comment in response.json():
            # Filter out bot comments
            if comment.get('user', {}).get('type') != 'Bot':
                comments.append({
                    'type': 'review_comment',
                    'body': comment.get('body', ''),
                    'path': comment.get('path', ''),
                    'user': comment.get('user', {}).get('login', 'unknown')
                })
    
    # Get issue comments (general PR comments)
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        for comment in response.json():
            # Filter out bot comments
            if comment.get('user', {}).get('type') != 'Bot':
                comments.append({
                    'type': 'issue_comment',
                    'body': comment.get('body', ''),
                    'user': comment.get('user', {}).get('login', 'unknown')
                })
    
    # Get PR reviews (approve/request changes with comments)
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/reviews'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        for review in response.json():
            if review.get('user', {}).get('type') != 'Bot' and review.get('body'):
                comments.append({
                    'type': 'pr_review',
                    'body': review.get('body', ''),
                    'state': review.get('state', ''),
                    'user': review.get('user', {}).get('login', 'unknown')
                })
    
    return comments


def load_system_prompt(prompt_file: str) -> str:
    """Load the current system prompt from file."""
    prompt_path = Path(prompt_file)
    
    if not prompt_path.exists():
        print(f"System prompt file '{prompt_file}' not found")
        return ""
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def save_system_prompt(prompt_file: str, content: str) -> bool:
    """Save the updated system prompt to file."""
    prompt_path = Path(prompt_file)
    
    try:
        # Ensure directory exists
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error saving system prompt: {e}")
        return False


def analyze_comments_and_update_prompt(client: OpenAI, current_prompt: str, comments: list, pr_number: int) -> tuple[str, bool]:
    """Use AI to analyze comments and determine if/how to update the prompt."""
    
    if not comments:
        print("No human review comments found in this PR")
        return current_prompt, False
    
    # Format comments for analysis
    comments_text = "\n\n".join([
        f"**Comment by {c['user']} ({c['type']}):**\n{c['body']}"
        for c in comments
    ])
    
    analysis_prompt = f"""You are an expert at analyzing code review feedback and improving code review guidelines.

## Task
Analyze the following human review comments from a merged pull request and determine if any feedback patterns should be incorporated into the code review system prompt.

## Current System Prompt:
```
{current_prompt}
```

## Human Review Comments from PR #{pr_number}:
{comments_text}

## Instructions

1. Identify recurring patterns or valuable insights from the human reviews that could improve future AI code reviews
2. Look for:
   - Specific coding standards or conventions the team follows
   - Common issues that humans catch but might not be in the current prompt
   - Team-specific best practices
   - Security, performance, or quality concerns specific to this codebase
   
3. If you find valuable insights to add, update the system prompt by:
   - Adding new guidelines that capture these insights
   - Enhancing existing sections with more specific guidance
   - Preserving the overall structure and format of the prompt
   
4. Do NOT:
   - Remove existing valuable guidelines
   - Make changes if the comments are too specific to a single PR
   - Add redundant information already covered in the prompt
   - Significantly change the tone or format of the prompt

## Response Format

First, provide a brief analysis of the comments (2-3 sentences).

Then, if updates are warranted, output the COMPLETE updated system prompt between <updated_prompt> and </updated_prompt> tags.

If no updates are needed, output <no_update_needed> with a brief explanation.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        result = response.choices[0].message.content
        
        # Check if update is needed
        if '<no_update_needed>' in result:
            print("Analysis complete: No updates needed")
            return current_prompt, False
        
        # Extract updated prompt
        if '<updated_prompt>' in result and '</updated_prompt>' in result:
            start = result.find('<updated_prompt>') + len('<updated_prompt>')
            end = result.find('</updated_prompt>')
            updated_prompt = result[start:end].strip()
            
            # Add update metadata
            timestamp = datetime.now().strftime('%Y-%m-%d')
            update_note = f"\n\n<!-- Last updated: {timestamp} based on PR #{pr_number} review insights -->"
            
            # Check if there's already an update note and replace it
            if '<!-- Last updated:' in updated_prompt:
                import re
                updated_prompt = re.sub(
                    r'<!-- Last updated:.*?-->',
                    update_note.strip(),
                    updated_prompt
                )
            else:
                updated_prompt += update_note
            
            print("Analysis complete: Updates identified")
            return updated_prompt, True
        
        print("Could not parse AI response for prompt update")
        return current_prompt, False
        
    except Exception as e:
        print(f"Error analyzing comments: {e}")
        return current_prompt, False


def main():
    # Get environment variables
    github_token = get_env_var('GITHUB_TOKEN')
    openai_api_key = get_env_var('OPENAI_API_KEY')
    system_prompt_file = os.environ.get('SYSTEM_PROMPT_FILE', '.github/prompts/system_prompt.md')
    pr_number = int(get_env_var('PR_NUMBER'))
    repo_owner = get_env_var('REPO_OWNER')
    repo_name = get_env_var('REPO_NAME')
    
    print(f"Analyzing review comments from PR #{pr_number}...")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=openai_api_key)
    
    # Get review comments
    comments = get_review_comments(repo_owner, repo_name, pr_number, github_token)
    print(f"Found {len(comments)} human review comment(s)")
    
    if not comments:
        print("No human review comments to analyze. Skipping prompt update.")
        return
    
    # Load current system prompt
    current_prompt = load_system_prompt(system_prompt_file)
    if not current_prompt:
        print("Could not load current system prompt. Skipping update.")
        return
    
    # Analyze and potentially update
    updated_prompt, was_updated = analyze_comments_and_update_prompt(
        client, current_prompt, comments, pr_number
    )
    
    if was_updated:
        if save_system_prompt(system_prompt_file, updated_prompt):
            print(f"Successfully updated system prompt: {system_prompt_file}")
        else:
            print("Failed to save updated system prompt")
            sys.exit(1)
    else:
        print("No changes made to system prompt")


if __name__ == '__main__':
    main()

