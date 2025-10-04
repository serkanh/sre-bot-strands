# !/bin/bash

# Create Pull Request with Analysis

Create a comprehensive pull request with detailed explanatory comments comparing changes between the current branch and main.

## Context Collection

First, gather the necessary information about the current state and run these in parallel:

!`git status --porcelain`
!`git branch --show-current`
!`git log --oneline main..HEAD --max-count=10`
!`git diff main...HEAD --stat`

## Your Task

**Step 1: Analyze the Changes**

1. Run `git diff main...HEAD` to get the complete diff between main and current branch
2. Analyze all modified, added, and deleted files
3. Identify the key changes, their purpose, and impact
4. Group related changes into logical categories (features, fixes, refactoring, etc.)

**Step 2: Generate PR Title and Description**

1. Create a clear, descriptive PR title following conventional commit format if applicable
2. Write a comprehensive PR description that includes:
   - **Overview**: Brief summary of what this PR accomplishes
   - **Changes Made**: Detailed breakdown of modifications by file/component
   - **Why These Changes**: Explanation of the reasoning behind each major change
   - **Testing**: How the changes have been tested or should be tested
   - **Breaking Changes**: Any breaking changes and migration notes
   - **Screenshots/Examples**: If UI changes are involved

**Step 3: Create Detailed PR Comments**
For each significant file change:

1. Add inline comments explaining complex logic changes
2. Highlight any potential concerns or areas for reviewer attention
3. Explain design decisions and trade-offs made
4. Point out any dependencies or related changes

**Step 4: Create the Pull Request**

1. Ensure all changes are committed
2. Push the current branch to remote if not already pushed
3. Use GitHub CLI to create the PR: `gh pr create --title "TITLE" --body "DESCRIPTION"`
4. Add any relevant labels, assignees, or reviewers
5. If inline comments are needed, use `gh pr comment` to add file-specific explanations
6. If there are existing comments on the pr, prompt user to replace or append to existing comments.

**Step 5: Final Review**

1. Display a summary of what was created
2. Provide the PR URL for easy access
3. Suggest any follow-up actions (reviewers to assign, tests to run, etc.)

## Guidelines

- **Be Thorough**: Explain not just what changed, but why it changed
- **Consider the Reviewer**: Make it easy for reviewers to understand the context and intent
- **Highlight Important Areas**: Call attention to complex logic, potential issues, or critical changes
- **Use Clear Language**: Write explanations that both technical and non-technical team members can understand
- **Include Context**: Reference any related issues, tickets, or discussions

## Arguments

You can optionally provide additional context: `$ARGUMENTS`

If arguments are provided, incorporate them into the PR description and analysis.

## Required Tools

This command requires the following tools to be enabled:

- `Bash(git *)` - For git operations
- `Bash(gh *)` - For GitHub CLI operations (ensure gh is authenticated)

## Example Usage

```bash
# Basic usage
/user:create-detailed-pr

# With additional context
/user:create-detailed-pr "Relates to issue #123, implements new authentication flow"
```

## Notes

- This command assumes you have GitHub CLI (`gh`) installed and authenticated
- The current branch should have commits that differ from main
- Large diffs may require multiple comments due to GitHub API limits
- Consider running this command in auto mode for seamless execution
EOF
