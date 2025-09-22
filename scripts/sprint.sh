#!/usr/bin/env bash

{
    echo "# Current Sprint Issues 🏃"
    echo ""
    echo "| Issue | Title | Assignee |"
    echo "|-------|-------|----------|"

    gh project item-list 28 --owner worldbank --format json \
        | jq -r '.items[]
              | select(.status=="🏃This Sprint")
              | "| [#\(.content.number)](\(.content.url)) | \(.content.title) | \(if .assignees then (.assignees | join(", ")) else "unassigned" end) |"'
} | glow
