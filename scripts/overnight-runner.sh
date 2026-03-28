#!/bin/bash
# Overnight Runner - Cron wrapper for atlas-overnight
#
# Usage: Add to crontab for scheduled overnight runs
#   0 23 * * * /path/to/overnight-runner.sh
#
# Features:
# - Checks if already running (prevents duplicates)
# - Logs output with timestamps
# - Sends notification on completion (optional)

set -e

# Configuration
ATLAS_ROOT="${HOME}/ai-workspace/atlas"
LOG_DIR="${HOME}/.claude/data/overnight-logs"
LOCK_FILE="${LOG_DIR}/overnight.lock"
PYTHON_PATH="/usr/bin/python3"  # Adjust if needed

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Load API keys
ENV_FILE="${HOME}/.claude/config/overnight.env"
if [ -f "${ENV_FILE}" ]; then
    source "${ENV_FILE}"
fi

# Check for lock file (prevent duplicate runs)
if [ -f "${LOCK_FILE}" ]; then
    pid=$(cat "${LOCK_FILE}")
    if kill -0 "${pid}" 2>/dev/null; then
        echo "$(date): Overnight operator already running (PID: ${pid})" >> "${LOG_DIR}/runner.log"
        exit 0
    fi
    # Stale lock file, remove it
    rm -f "${LOCK_FILE}"
fi

# Create lock file
echo $$ > "${LOCK_FILE}"

# Cleanup on exit
cleanup() {
    rm -f "${LOCK_FILE}"
}
trap cleanup EXIT

# Log start
DATE=$(date +%Y-%m-%d)
LOG_FILE="${LOG_DIR}/session-${DATE}.log"

echo "========================================" >> "${LOG_FILE}"
echo "Overnight Session Started: $(date)" >> "${LOG_FILE}"
echo "========================================" >> "${LOG_FILE}"

# Activate virtual environment if it exists
if [ -f "${ATLAS_ROOT}/.venv/bin/activate" ]; then
    source "${ATLAS_ROOT}/.venv/bin/activate"
fi

# Run the overnight operator
cd "${ATLAS_ROOT}"
${PYTHON_PATH} scripts/atlas-overnight run >> "${LOG_FILE}" 2>&1
EXIT_CODE=$?

# Log completion
echo "" >> "${LOG_FILE}"
echo "========================================" >> "${LOG_FILE}"
echo "Overnight Session Completed: $(date)" >> "${LOG_FILE}"
echo "Exit code: ${EXIT_CODE}" >> "${LOG_FILE}"
echo "========================================" >> "${LOG_FILE}"

# Optional: Send notification
# Uncomment and configure as needed:
#
# BRIEFING_DIR="${HOME}/.claude/data/overnight-briefings"
# BRIEFING_FILE="${BRIEFING_DIR}/briefing-${DATE}.md"
#
# if [ -f "${BRIEFING_FILE}" ]; then
#     # Email notification
#     # mail -s "ATLAS Overnight Report - ${DATE}" your@email.com < "${BRIEFING_FILE}"
#
#     # Or use a notification service
#     # curl -X POST -d "text=$(cat ${BRIEFING_FILE})" https://your.webhook.url
# fi

exit ${EXIT_CODE}
