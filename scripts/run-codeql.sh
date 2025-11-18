#!/usr/bin/env bash

# CodeQL Analysis Script for GEEST
# This script creates a CodeQL database and runs security analysis
# Usage: ./scripts/run-codeql.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_PATH="./codeql-database"
RESULTS_FILE="codeql-results.sarif"
LANG="python"

echo -e "${BLUE}🔎 CodeQL Analysis for GEEST${NC}"
echo "=================================="

# Check if CodeQL CLI is installed
if ! command -v codeql &>/dev/null; then
  echo -e "${RED}❌ CodeQL CLI not found. Please install it first:${NC}"
  echo "   1. Download from: https://github.com/github/codeql-cli-binaries/releases"
  echo "   2. Extract and add to PATH"
  echo "   3. Or install via: gh extension install github/gh-codeql"
  exit 1
fi

# Clean up previous database
if [ -d "$DB_PATH" ]; then
  echo -e "${YELLOW}🧹 Removing existing database...${NC}"
  rm -rf "$DB_PATH"
fi

# Create CodeQL database
echo -e "${BLUE}📊 Creating CodeQL database...${NC}"
if ! codeql database create "$DB_PATH" \
  --language="$LANG" \
  --source-root=. \
  --overwrite \
  --quiet; then
  echo -e "${RED}❌ Failed to create CodeQL database${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Database created successfully${NC}"

# Run CodeQL analysis
echo -e "${BLUE}🔍 Running CodeQL analysis...${NC}"
if ! codeql database analyze "$DB_PATH" \
  --format=sarifv2.1.0 \
  --output="$RESULTS_FILE" \
  --download \
  --quiet; then
  echo -e "${RED}❌ CodeQL analysis failed${NC}"
  exit 1
fi

echo -e "${GREEN}✅ CodeQL analysis completed${NC}"

# Check if results file exists and has findings
if [ -f "$RESULTS_FILE" ]; then
  # Count findings
  FINDINGS=$(jq '.runs[0].results | length' "$RESULTS_FILE" 2>/dev/null || echo "0")

  if [ "$FINDINGS" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $FINDINGS security findings${NC}"
    echo -e "${BLUE}📄 Results saved to: $RESULTS_FILE${NC}"

    # Show summary of findings if jq is available
    if command -v jq &>/dev/null; then
      echo -e "\n${BLUE}Summary of findings:${NC}"
      jq -r '.runs[0].results[] | "\(.ruleId): \(.message.text)"' "$RESULTS_FILE" | head -10

      if [ "$FINDINGS" -gt 10 ]; then
        echo "... and $((FINDINGS - 10)) more findings"
      fi
    fi

    echo -e "\n${BLUE}💡 To view detailed results:${NC}"
    echo "   - Upload $RESULTS_FILE to GitHub Security tab"
    echo "   - Use: codeql database serve $DB_PATH"
    echo "   - Or use VS Code with CodeQL extension"

    exit 1
  else
    echo -e "${GREEN}🎉 No security findings detected!${NC}"
  fi
else
  echo -e "${RED}❌ Results file not created${NC}"
  exit 1
fi

# Clean up database (optional - keep for debugging)
# rm -rf "$DB_PATH"

echo -e "${GREEN}✅ CodeQL analysis completed successfully${NC}"
