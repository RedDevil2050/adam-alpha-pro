#!/bin/bash

echo "🛑 Emergency Shutdown Initiated..."
docker-compose -f deploy/docker-compose.yml down
echo "System halted. Check logs for details."
