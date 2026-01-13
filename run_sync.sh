#!/bin/bash
# ===========================================================
# Golf Pick 'Em - Sync Task Runner
# ===========================================================
set -e

# Define paths
PROJECT_DIR="/home/GolfPickEm/Golf_Pick_Em"
VENV_DIR="/home/GolfPickEm/.virtualenvs/golfpickem"
ENV_CONFIG="$PROJECT_DIR/env_config.sh"

# Verify env_config.sh exists
if [ ! -f "$ENV_CONFIG" ]; then
    echo "ERROR: $ENV_CONFIG not found!"
    exit 1
fi

# Load credentials from gitignored config file
source "$ENV_CONFIG"

# Verify API key is set
if [ -z "$SLASHGOLF_API_KEY" ] || [ "$SLASHGOLF_API_KEY" = "paste_your_api_key_here" ]; then
    echo "ERROR: SLASHGOLF_API_KEY not configured in env_config.sh"
    exit 1
fi

# Set Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=production
export SYNC_MODE=free
export DATABASE_URL="sqlite:///$PROJECT_DIR/golf_pickem.db"

# Change to project directory
cd "$PROJECT_DIR"

# Activate the virtualenv
source "$VENV_DIR/bin/activate"

# Check what mode was requested
MODE="$1"

if [ -z "$MODE" ]; then
    echo "ERROR: No sync mode specified."
    echo "Usage: ./run_sync.sh [schedule|field|results]"
    exit 1
fi

# Log start time
echo "=========================================="
echo "Golf Pick 'Em Sync: $MODE"
echo "Started: $(date)"
echo "=========================================="

# Run the Flask sync command
"$VENV_DIR/bin/python3" -m flask sync-run --mode "$MODE"

# Log completion
echo "=========================================="
echo "Completed: $(date)"
echo "=========================================="