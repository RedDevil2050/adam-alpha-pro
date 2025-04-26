#!/bin/bash

set -e  # Exit on any error

echo "🚀 Initiating Production Launch Sequence..."

# Load production config
if [ ! -f "deploy/production-config.env" ]; then
    echo "❌ Production config not found!"
    exit 1
fi
source deploy/production-config.env

# Run pre-flight checks
echo "Running pre-flight checks..."
./deploy/test-system.sh

# Create backup
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp deploy/docker-compose.yml $BACKUP_DIR/
cp deploy/production-config.env $BACKUP_DIR/

# Deploy system
echo "🔥 Deploying production system..."
docker-compose -f deploy/docker-compose.yml --env-file deploy/production-config.env up -d

# Monitor startup
echo "📊 Monitoring startup..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ System successfully launched!"
        echo "🔍 Monitor your system at: http://localhost:8000/health"
        echo "📈 Trading pairs active: $ALLOWED_PAIRS"
        echo "⚠️ Emergency shutdown: ./deploy/shutdown.sh"
        exit 0
    fi
    echo "Waiting for system to stabilize... ($i/30)"
    sleep 2
done

echo "❌ System startup took too long. Check logs:"
docker-compose -f deploy/docker-compose.yml logs
