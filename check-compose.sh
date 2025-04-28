#!/bin/bash

echo "=== Docker Compose Configuration Check ==="
if [ -f docker-compose.yml ]; then
  docker-compose config
else
  echo "No docker-compose.yml found in current directory"
fi

echo -e "\n=== Docker Compose Service Status ==="
if [ -f docker-compose.yml ]; then
  docker-compose ps
else
  echo "No docker-compose.yml found in current directory"
fi
