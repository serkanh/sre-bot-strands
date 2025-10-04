---
allowed-tools: Bash(git:*), Bash(gh:*)
argument-hint: [version-type]
description: Create Release Notes
---

# Generate Release Notes Draft

Generate a GitHub release draft by analyzing commits between the current HEAD and the main/master branch.

## Arguments

- `$1`: Optional version type override - must be "major", "minor", or "patch" (if omitted, auto-detect based on commits)

## Context Collection

!`git fetch --all`
!`git branch --show-current`
!`git remote show origin | grep 'HEAD branch'`
!`gh release list --limit 1 2>/dev/null || echo "No releases found"`
!`git log --oneline main..HEAD 2>/dev/null || git log --oneline master..HEAD`

## Steps

### 1. Determine Default Branch and Validate

- Detect the default branch (main vs master) automatically
- Verify there are commits to compare between HEAD and the default branch
- If no differences exist, inform the user and exit

### 2. Analyze Commits

Get all commits between the default branch and HEAD: `git log --oneline --pretty=format:'%h %s' main..HEAD` (or master..HEAD)

Categorize commits by parsing commit message prefixes:
- 🚀 Features: feat:, feature:
- 🐛 Bug Fixes: fix:, bugfix:
- 💥 Breaking Changes: BREAKING CHANGE:, breaking:
- 📚 Documentation: docs:, doc:
- ♻️  Refactor: refactor:, refact:
- 🧪 Tests: test:, tests:
- ⚡ Performance: perf:, performance:
- 🔧 Chore: chore:, build:, ci:
- Other: uncategorized commits

### 3. Determine Version

1. Get current version from `gh release list --limit 1`
2. If no releases found, start with `1.0.0`
3. If `$1` is provided, use that increment type
4. Otherwise, auto-increment based on changes:
   - Major (X.0.0): Breaking changes detected
   - Minor (X.Y.0): New features (no breaking changes)
   - Patch (X.Y.Z): Only fixes, docs, or other changes

### 4. Generate Release Notes

Format release notes as:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### 🚀 Features
- [commit] Description

### 🐛 Bug Fixes
- [commit] Description

### 💥 Breaking Changes
- [commit] Description

(Include other sections only if they have content)

**Full Changelog**: https://github.com/OWNER/REPO/compare/PREV_VERSION...NEW_VERSION
```

### 5. Create GitHub Draft Release

1. Display the generated release notes
2. Create GitHub draft release using:
   - Tag format: `X.Y.Z` (NO 'v' prefix)
   - Title: Version number only
   - Draft mode: Always create as draft
   - Example: `gh release create 0.6.0 --draft --title "0.6.0" --notes "..."`
3. Display the release URL

## Examples

```bash
/release-notes              # Auto-detect version increment
/release-notes major        # Force major version increment
/release-notes minor        # Force minor version increment
/release-notes patch        # Force patch version increment
```
