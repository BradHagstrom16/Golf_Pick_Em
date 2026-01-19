#!/bin/bash
# ===========================================================
# Golf Pick 'Em - Email Reminder Runner
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

# Load credentials
source "$ENV_CONFIG"

# Set Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=production
export DATABASE_URL="sqlite:///$PROJECT_DIR/golf_pickem.db"

# Change to project directory
cd "$PROJECT_DIR"

# Activate the virtualenv
source "$VENV_DIR/bin/activate"

# Run the reminder script
"$VENV_DIR/bin/python3" send_reminders.py