#!/bin/bash

LOG_DIR=".ai/logs"
mkdir -p $LOG_DIR

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/${TIMESTAMP}_session.md"

echo "# Session Log: $TIMESTAMP" > $LOG_FILE
echo "" >> $LOG_FILE
echo "## Status" >> $LOG_FILE
echo "" >> $LOG_FILE
echo "- Branch: $(git branch --show-current)" >> $LOG_FILE
echo "- Commit: $(git rev-parse --short HEAD)" >> $LOG_FILE
echo "- Python: $(python --version)" >> $LOG_FILE
echo "" >> $LOG_FILE
echo "## What was done" >> $LOG_FILE
echo "" >> $LOG_FILE
echo "TODO: Fill this section" >> $LOG_FILE
echo "" >> $LOG_FILE
echo "## Current Status" >> $LOG_FILE
echo "" >> $LOG_FILE
echo "TODO: Fill this section" >> $LOG_FILE
echo "" >> $LOG_FILE
echo "## Next Steps" >> $LOG_FILE
echo "" >> $LOG_FILE
echo "TODO: Fill this section" >> $LOG_FILE
echo "" >> $LOG_FILE
echo "## Errors" >> $LOG_FILE
echo "" >> $LOG_FILE
echo "None yet" >> $LOG_FILE

echo "Log created: $LOG_FILE"
