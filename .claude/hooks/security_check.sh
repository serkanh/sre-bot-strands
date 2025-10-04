#!/usr/bin/env bash
set -e

# Read JSON input from stdin
INPUT=$(cat)

# Extract the command that's about to be run
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Define dangerous patterns
DANGEROUS_PATTERNS=(
    "rm -rf /"
    "rm -rf /*"
    "chmod 777"
    "curl.*\|.*bash"
    "wget.*\|.*bash"
    "> /dev/sda"
    "dd if=/dev/zero"
    "mkfs"
    ":|:"  # Fork bomb
)

# Check for dangerous patterns
for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        # Block the command
        echo "{\"continue\": false, \"stopReason\": \"⚠️ Blocked dangerous command: Pattern '$pattern' detected\"}"
        exit 0
    fi
done

# Check for sudo usage (might want to handle separately)
if echo "$COMMAND" | grep -q "^sudo\|[[:space:]]sudo[[:space:]]"; then
    echo "{\"continue\": false, \"stopReason\": \"⚠️ Sudo commands require manual approval\"}"
    exit 0
fi

# Check for operations on sensitive files
SENSITIVE_PATHS=(
    "/etc/passwd"
    "/etc/shadow"
    ".ssh/id_rsa"
    ".ssh/id_ed25519"
    ".env"
    ".aws/credentials"
)

for path in "${SENSITIVE_PATHS[@]}"; do
    if echo "$COMMAND" | grep -q "$path"; then
        echo "{\"continue\": false, \"stopReason\": \"⚠️ Blocked: Command affects sensitive file: $path\"}"
        exit 0
    fi
done

# Log the command for auditing (optional)
echo "[$(date -Iseconds)] Approved: $COMMAND" >> ~/.claude/logs/command_audit.log

# Allow the command to proceed
echo '{"continue": true}
