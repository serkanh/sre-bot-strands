---
allowed-tools: Bash(git:*), Bash(gh:*)
description: Create Release Notes
---

# Generate Release Notes and Increment Version

Generate comprehensive release notes by comparing the current HEAD with the main/master branch, automatically increment versions, and update RELEASE_NOTES.md.

## Context Collection

First, gather the necessary information about the repository state:

!`git status --porcelain`
!`git fetch --all` # To get the latest releases
!`git branch --show-current`
!`git remote show origin | grep 'HEAD branch'`
!`gh release list --limit 1 2>/dev/null || echo "No releases found"`
!`git log --oneline main..HEAD 2>/dev/null || git log --oneline master..HEAD`
!`git diff --stat main...HEAD 2>/dev/null || git diff --stat master...HEAD`

## Your Task

**Step 1: Determine Default Branch and Validate Repository**

1. Detect the default branch (main vs master) automatically using git commands
2. Ensure the repository is clean or has only staged changes
3. Verify there are commits to compare between HEAD and the default branch
4. If no differences exist, inform the user and exit gracefully

**Step 2: Generate Git History Analysis**

1. Get all commits between the default branch and HEAD: `git log --oneline --pretty=format:'%h %s' main..HEAD` (or master..HEAD)
2. Parse commit messages for conventional commit patterns (feat:, fix:, BREAKING CHANGE:, etc.)
3. Categorize commits into:
   - **🚀 Features** (feat:, feature:)
   - **🐛 Bug Fixes** (fix:, bugfix:)
   - **💥 Breaking Changes** (BREAKING CHANGE:, breaking:)
   - **📚 Documentation** (docs:, doc:)
   - **🎨 Style** (style:, format:)
   - **♻️  Refactor** (refactor:, refact:)
   - **🧪 Tests** (test:, tests:)
   - **⚡ Performance** (perf:, performance:)
   - **🔧 Chore** (chore:, build:, ci:)
   - **Other** (commits that don't match patterns)

**Step 3: Determine Version Increment**

1. First check the latest GitHub release using `gh release list --limit 1` to get the current version
2. If no GitHub releases found, fall back to checking existing RELEASE_NOTES.md for version patterns like `## [1.2.3]` or `# Version 1.2.3`
3. If no version found anywhere, start with `1.0.0`
4. Auto-increment version based on change types:
   - **Major** (X.0.0): If breaking changes detected
   - **Minor** (X.Y.0): If new features detected (and no breaking changes)
   - **Patch** (X.Y.Z): If only bug fixes, docs, or other changes
5. Allow override with optional argument: `$1` can be "major", "minor", or "patch"

**Step 4: Generate Release Notes Content**

Create formatted release notes with:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### 🚀 Features
- [commit] Description (if any features)

### 🐛 Bug Fixes
- [commit] Description (if any fixes)

### 💥 Breaking Changes
- [commit] Description (if any breaking changes)

### 📚 Documentation
- [commit] Description (if any doc changes)

### Other Changes
- [commit] Description (for uncategorized commits)

**Full Changelog**: https://github.com/OWNER/REPO/compare/PREV_VERSION...NEW_VERSION
```

**Step 5: Update Version in Project Files**

Search for and update version numbers in common files:

1. **package.json** - Update `version` field
2. **Cargo.toml** - Update `version` field in `[package]` section
3. **pyproject.toml** - Update `version` field in `[project]` or `[tool.poetry]` section
4. **setup.py** - Update `version=` parameter
5. **pubspec.yaml** - Update `version:` field (Flutter/Dart)
6. **build.gradle** - Update `version` in gradle files (Android/Java)
7. **pom.xml** - Update `<version>` in Maven files (Java)
8. **composer.json** - Update `version` field (PHP)
9. **Dockerfile** - Update any version labels
10. **VERSION** file - Update plain text version files

Only update files that exist in the current project.

**Step 6: Update RELEASE_NOTES.md**

1. If RELEASE_NOTES.md doesn't exist, create it with a header
2. If it exists, prepend the new release notes to the top (after any header)
3. Maintain proper markdown formatting and structure
4. Preserve existing content

**Step 7: Create GitHub Release and Summary**

1. Display the generated release notes
2. Show which files were updated with new versions
3. List the changes that would be committed
4. Create a GitHub draft release using `gh release create`:
   - **Tag format**: Use `X.Y.Z` format (e.g., `0.6.0`, `1.2.3`) - **DO NOT include 'v' prefix**
   - **Title**: Use the same version format without 'v' prefix
   - **Draft mode**: Create as draft for review before publishing
   - Example: `gh release create 0.6.0 --draft --title "0.6.0: Release Title"`
5. Display the release note page URL to the user

## Arguments

- `$1`: Optional version type override ("major", "minor", "patch")
- `$ARGUMENTS`: Any additional context for the release notes

## Examples

```bash
# Auto-detect version increment based on commits
/release-notes

# Force a major version increment
/release-notes major

# Force a minor version increment with context
/release-notes minor "Special release for new API features"
```

## Required Tools

- `Bash(git *)` - For git operations
- `Bash(gh *)` - For GitHub CLI operations to check releases
- `Read` - To read existing files
- `Write` - To create/update files
- `Edit` - To modify existing files
- `Grep` - To search for version patterns

## Error Handling

- Handle cases where no commits exist between branches
- Gracefully handle missing version files
- Validate git repository state before proceeding
- Provide clear error messages for common issues

## Notes

- This command works with any git repository
- Supports both main and master as default branches
- Follows semantic versioning principles
- Conventional commit format is recommended but not required
- Generated release notes can be manually edited after creation
- Consider running in auto mode for seamless execution
