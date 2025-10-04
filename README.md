# Claude Code Bootstrap

A bootstrap repository for Claude Code projects with opinionated hooks and commands.

## Components

### `.claude/settings.json`
Configuration file that registers hooks for automated code quality and security checks.

### `.claude/hooks/`
Automated hooks that run during Claude Code operations:

- **`format_code.sh`** - Runs after file edits (Edit/Write) to automatically format code using language-specific formatters (Prettier, Black, gofmt, rustfmt)
- **`security_check.sh`** - Runs before Bash commands to block dangerous patterns (rm -rf /, sudo, sensitive file operations) and logs all approved commands for auditing

### `.claude/commands/`
Custom slash commands for structured workflows:

- **`/generate-prp`** - Creates comprehensive PRPs (Prompt Request Proposals) with codebase research and implementation blueprints
- **`/execute-prp`** - Executes PRPs for one-pass feature implementation

### `.claude/agents/`
Specialized AI agents for specific tasks:

- **`senior-systems-architect`** - Architecture expert focused on modular, black-box design principles for building maintainable systems. Analyzes codebases for architectural patterns and suggests refactoring strategies.
- **`library-docs-researcher`** - Documentation researcher that finds comprehensive library documentation using Context7 and web search. Provides installation guides, usage examples, and API references for any library or framework.

## Usage

Clone this repository as a starting point for new Claude Code projects. The hooks ensure code quality and security, while the commands provide structured approaches for complex feature development.
