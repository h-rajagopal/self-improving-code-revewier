# 🤖 Self-Improving Code Review Agent

An AI-powered code review agent that uses GitHub Actions to automatically review pull requests and continuously improves its review quality by learning from human feedback.

## ✨ Features

- **Automated Code Reviews**: AI reviews every PR and provides detailed, actionable feedback
- **Dynamic System Prompt**: The review guidelines are stored in a configurable file, not hardcoded
- **Self-Improving**: Analyzes human review comments when PRs are merged and updates the system prompt
- **Configurable**: Easy to customize the API key and system prompt file location
- **Non-Intrusive**: Creates separate PRs for system prompt updates, requiring human approval

## 📁 Project Structure

```
.github/
├── workflows/
│   ├── code-review.yml          # Triggers on PR open/update to review code
│   └── update-system-prompt.yml # Triggers on PR merge to update system prompt
├── scripts/
│   ├── code_reviewer.py         # AI code review logic
│   ├── prompt_updater.py        # System prompt update logic
│   └── requirements.txt         # Python dependencies
└── prompts/
    └── system_prompt.md         # The dynamic system prompt file
```

## 🚀 Setup

### 1. Copy Files to Your Repository

Copy the entire `.github` folder to your repository's root directory.

### 2. Configure Secrets

Go to your repository's **Settings → Secrets and variables → Actions** and add:

| Secret Name | Description |
|-------------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key for ChatGPT access |

> Note: `GITHUB_TOKEN` is automatically provided by GitHub Actions.

### 3. Configure Variables (Optional)

Go to **Settings → Secrets and variables → Actions → Variables** and add:

| Variable Name | Default Value | Description |
|---------------|---------------|-------------|
| `SYSTEM_PROMPT_FILE` | `.github/prompts/system_prompt.md` | Path to your system prompt file |

### 4. Customize the System Prompt

Edit `.github/prompts/system_prompt.md` to include your team's specific:
- Coding standards and conventions
- Security requirements
- Performance expectations
- Documentation guidelines
- Any other team-specific rules

## 🔄 How It Works

### Code Review Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PR Created/   │────▶│  AI Reviews     │────▶│  Comments       │
│   Updated       │     │  Code Changes   │     │  Posted on PR   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. Developer opens or updates a pull request
2. The `code-review.yml` workflow triggers
3. AI reads the dynamic system prompt from the configured file
4. AI reviews all changed code files
5. Review comments are posted on the PR

### Self-Improvement Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PR Merged     │────▶│  Analyze Human  │────▶│  Create PR for  │
│                 │     │  Review Comments│     │  Prompt Update  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. Developer merges a PR after human review
2. The `update-system-prompt.yml` workflow triggers
3. AI analyzes all human review comments from the PR
4. If patterns are identified that could improve future reviews:
   - The system prompt is updated
   - A new PR is created with the changes
5. Team reviews and merges the prompt update PR

## 🎯 Use Cases

### Example: Adding Team-Specific Guidelines

**Before**: The AI might not know your team uses a specific error handling pattern.

**Human Review Comment**: 
> "Please use our `Result<T>` pattern instead of throwing exceptions here."

**After PR Merge**: The AI analyzes this comment and updates the system prompt:

```markdown
## Team-Specific Guidelines

### Error Handling
- Prefer using the `Result<T>` pattern over throwing exceptions
- Only throw exceptions for truly exceptional cases
```

**Future Reviews**: The AI will now suggest using `Result<T>` pattern in applicable situations.

## ⚙️ Configuration Options

### Supported File Types

By default, the agent reviews these file types:
- Python (`.py`)
- JavaScript/TypeScript (`.js`, `.ts`, `.jsx`, `.tsx`)
- Java (`.java`)
- Go (`.go`)
- Rust (`.rs`)
- C/C++ (`.c`, `.cpp`, `.h`, `.hpp`)

To modify, edit the `files` filter in `.github/workflows/code-review.yml`.

### AI Model

The default model is `gpt-4o`. To change it, modify the `model` parameter in:
- `.github/scripts/code_reviewer.py`
- `.github/scripts/prompt_updater.py`

## 🔒 Security Considerations

- The `OPENAI_API_KEY` is stored as a GitHub secret and never exposed in logs
- Bot comments are filtered out when analyzing review feedback
- System prompt updates require human approval via PR review
- The agent only has read access to code and write access to PR comments

## 🐛 Troubleshooting

### Reviews Not Appearing

1. Check that `OPENAI_API_KEY` secret is set correctly
2. Verify the workflow has proper permissions
3. Check the Actions tab for workflow run logs

### System Prompt Not Updating

1. Ensure there are human (non-bot) review comments on the merged PR
2. Check the workflow logs for analysis results
3. Verify the `SYSTEM_PROMPT_FILE` variable points to an existing file

### Rate Limiting

If you hit OpenAI rate limits:
- Consider using a higher-tier API plan
- Reduce the number of files reviewed per PR
- Add delays between API calls in the scripts

## 📝 License

MIT License - feel free to use and modify for your projects.

## 🤝 Contributing

Contributions are welcome! Please open an issue or PR to suggest improvements.

---

*Built with ❤️ to make code reviews more consistent and helpful.*

