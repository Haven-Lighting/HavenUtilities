#!/bin/bash

# Script to run the Marquee App
echo "Starting Marquee App..."

# Change to the Marquee_App directory
cd "$(dirname "$0")/Marquee_App"

# Run the app with the virtual environment Python
../.venv/bin/python MarqueeApp.py
