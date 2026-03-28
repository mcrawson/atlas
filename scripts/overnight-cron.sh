#!/bin/bash
# Cron wrapper for ATLAS Overnight Operator
# Ensures proper environment setup for automated runs

set -e

# Paths
ATLAS_ROOT="$HOME/ai-workspace/atlas"
VENV="$ATLAS_ROOT/.venv"
SCRIPT="$ATLAS_ROOT/scripts/atlas-overnight"
LOG_DIR="$HOME/.claude/data/overnight-logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Log file with timestamp
LOG_FILE="$LOG_DIR/cron-$(date +%Y%m%d-%H%M%S).log"

# Activate virtual environment
source "$VENV/bin/activate"

# Run the overnight operator
echo "=== Overnight Session Started: $(date) ===" >> "$LOG_FILE"
python "$SCRIPT" run >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
echo "=== Overnight Session Ended: $(date) (exit: $EXIT_CODE) ===" >> "$LOG_FILE"

exit $EXIT_CODE
