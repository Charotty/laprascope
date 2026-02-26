#!/bin/bash
# Setup script for AR Laparoscopy cleanup timer
# This script installs the systemd service and timer for automatic job cleanup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="laprascope-cleanup"

echo "Setting up AR Laparoscopy cleanup timer..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should be run as the service user, not as root."
   echo "Please run as the user that runs the laprascope service."
   exit 1
fi

# Install service and timer files
echo "Installing systemd files..."
cp "$SCRIPT_DIR/$SERVICE_NAME.service" "$HOME/.config/systemd/user/"
cp "$SCRIPT_DIR/$SERVICE_NAME.timer" "$HOME/.config/systemd/user/"

# Create user systemd directory if it doesn't exist
mkdir -p "$HOME/.config/systemd/user"

# Reload systemd user daemon
echo "Reloading systemd user daemon..."
systemctl --user daemon-reload

# Enable and start the timer
echo "Enabling and starting timer..."
systemctl --user enable "$SERVICE_NAME.timer"
systemctl --user start "$SERVICE_NAME.timer"

# Show status
echo ""
echo "Timer status:"
systemctl --user list-timers "$SERVICE_NAME.timer"

echo ""
echo "Setup complete! The cleanup timer will:"
echo "- Run every 6 hours"
echo "- Delete jobs older than 24 hours"
echo "- Log to journal: journalctl --user -u $SERVICE_NAME.service"
echo ""
echo "To manually run cleanup: python cleanup_jobs.py"
echo "To preview cleanup: python cleanup_jobs.py --dry-run"
echo "To list all jobs: python cleanup_jobs.py --list"
