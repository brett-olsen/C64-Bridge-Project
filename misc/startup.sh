#!/bin/bash

# kill any existing process
killall -9 main.py
killall -9 chainlit

#!/usr/bin/env bash
set -e  # Exit on any error

# Check for Python 3.12
if ! command -v python3.12 &> /dev/null; then
    echo "Python 3.12 not found. Please install it first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python 3.12 virtual environment..."
    python3.12 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found! Skipping dependency installation."
fi

# Run the app
echo "Launching the app..."
chainlit run main.py
