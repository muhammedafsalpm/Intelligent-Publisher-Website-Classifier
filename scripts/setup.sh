#!/bin/bash
# scripts/setup.sh
# Setup script for the project

echo "Setting up Publisher Classifier..."

# Install dependencies
pip install -r requirements.txt

# Install playwright browsers
playwright install chromium

# Create necessary directories
mkdir -p chroma_db data scripts

# Copy example env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your configuration."
fi

echo "Setup complete!"
