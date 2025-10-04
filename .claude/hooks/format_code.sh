#!/usr/bin/env bash
set -e

# Read JSON input from stdin
INPUT=$(cat)

# Extract the file path from the tool response
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_response.filePath // .tool_input.file_path // empty')

# Exit if no file path found
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Check file extension and run appropriate formatter
if [[ "$FILE_PATH" == *.js || "$FILE_PATH" == *.jsx ]]; then
    echo "Formatting JavaScript file: $FILE_PATH"
    npx prettier --write "$FILE_PATH"
elif [[ "$FILE_PATH" == *.ts || "$FILE_PATH" == *.tsx ]]; then
    echo "Formatting TypeScript file: $FILE_PATH"
    npx prettier --write "$FILE_PATH"
elif [[ "$FILE_PATH" == *.py ]]; then
    echo "Formatting Python file: $FILE_PATH"
    black "$FILE_PATH" 2>/dev/null || true
elif [[ "$FILE_PATH" == *.go ]]; then
    echo "Formatting Go file: $FILE_PATH"
    gofmt -w "$FILE_PATH"
elif [[ "$FILE_PATH" == *.rs ]]; then
    echo "Formatting Rust file: $FILE_PATH"
    rustfmt "$FILE_PATH"
fi
