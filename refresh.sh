#!/bin/bash

echo "Starting system refresh..."

# Check if services are running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Services not running, starting up..."
    docker-compose up -d
    sleep 5
fi

# Run Python refresh script
python refresh.py

# Verify system status
curl -s http://localhost:8000/health

echo "Refresh complete!"
