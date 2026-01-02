#!/bin/bash
# Example runner script for rap battle system
# Usage: ./run_example.sh

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    set -a
    source .env
    set +a
else
    echo "No .env file found. Using environment variables or defaults..."
fi

# Run the main script
python main.py
