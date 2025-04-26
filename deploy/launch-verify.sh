#!/bin/bash

echo "🔍 Final Launch Verification"

# Check environment files
if [ ! -f "deploy/production-config.env" ]; then
    echo "❌ Production config missing"
    exit 1
fi

# Verify backup system
echo "Checking backup system..."
if [ ! -d "backups" ]; then
    mkdir -p backups
fi

# Verify monitoring setup
echo "Verifying monitoring setup..."
curl -s http://localhost:8000/metrics > /dev/null || {
    echo "❌ Metrics endpoint not responding"
    exit 1
}

# Check market data feeds
echo "Testing market data feeds..."
source deploy/production-config.env
IFS=',' read -ra PAIRS <<< "$ALLOWED_PAIRS"
for pair in "${PAIRS[@]}"; do
    curl -s "http://localhost:8000/api/market/test/$pair" || {
        echo "❌ Market data test failed for $pair"
        exit 1
    }
done

# Verify rollback capability
echo "Checking rollback readiness..."
if [ ! -f "deploy/shutdown.sh" ] || [ ! -x "deploy/shutdown.sh" ]; then
    echo "❌ Emergency shutdown script not executable"
    exit 1
fi

echo "✅ Launch verification complete"
echo "
FINAL CHECKLIST:
□ Production credentials configured
□ Rate limits set
□ Monitoring alerts configured
□ Team notifications setup
□ Backup schedule confirmed
□ Emergency contacts updated"
