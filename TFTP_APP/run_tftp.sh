#!/bin/bash

# Script to run TFTP application with sudo permissions
# This is needed because TFTP uses port 69 which requires root privileges

echo "Starting TFTP & UDP Utility with sudo permissions..."
echo "This is required to bind to port 69 for TFTP listening."
echo ""

# Change to the correct directory and run the Python script with sudo
cd /Users/joshfazekas/develop/HavenUtilities/TFTP_APP
sudo /opt/homebrew/bin/python3 /Users/joshfazekas/develop/HavenUtilities/TFTP_APP/TFTP.py
