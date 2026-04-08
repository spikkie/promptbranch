#!/bin/bash

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
pip install pytest httpx

echo "✅ Environment ready! Use 'source venv/bin/activate' to activate."


# Install Patchright-managed Chrome for the recommended channel="chrome" flow
patchright install chrome
