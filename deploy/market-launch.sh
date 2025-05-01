#!/bin/bash

set -e

echo "🚀 Starting Zion Market Analysis Platform Production Deployment..."

# Step 1: Retrieve secrets from Azure Key Vault and set them as environment variables
echo "🔑 Retrieving secrets from Azure Key Vault..."

# Azure Key Vault name
KEY_VAULT_NAME="zion-production-kv"

# Login to Azure if not already logged in
echo "Authenticating with Azure..."
az account show > /dev/null 2>&1 || az login

# Function to retrieve secret from Key Vault and set as environment variable
get_secret() {
    local secret_name=$1
    local env_var_name=$2
    
    echo "Retrieving $secret_name from Key Vault..."
    value=$(az keyvault secret show --name "$secret_name" --vault-name "$KEY_VAULT_NAME" --query "value" -o tsv)
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to retrieve $secret_name from Key Vault"
        exit 1
    fi
    
    # Export as environment variable
    export $env_var_name="$value"
    echo "✅ Secret $secret_name retrieved and set as $env_var_name"
}

# Retrieve all required secrets
get_secret "DbPassword" "DB_PASSWORD"
get_secret "GrafanaPassword" "GRAFANA_PASSWORD"
get_secret "JwtSecret" "JWT_SECRET"
get_secret "ApiPassHash" "API_PASS_HASH"
get_secret "AlphaVantageKey" "ALPHA_VANTAGE_KEY"
get_secret "YahooFinanceApiKey" "YAHOO_FINANCE_API_KEY"
get_secret "FinnhubApiKey" "FINNHUB_API_KEY"
get_secret "PolygonApiKey" "POLYGON_API_KEY"
get_secret "SlackWebhookUrl" "SLACK_WEBHOOK_URL"
get_secret "AlertEmail" "ALERT_EMAIL"

echo "🔒 All secrets have been retrieved from Azure Key Vault"

# Step 2: Validate Docker and Docker Compose installation
echo "🔍 Validating Docker configuration..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

if ! docker-compose --version > /dev/null 2>&1; then
    echo "❌ Docker Compose not found. Please install Docker Compose and try again."
    exit 1
fi

# Step 3: Validate Docker Compose configuration
echo "🧪 Validating Docker Compose configuration..."
if ! docker-compose config -q; then
    echo "❌ Docker Compose configuration is invalid."
    exit 1
fi

# Step 4: Generate .env file for Docker Compose with Azure Key Vault secrets
echo "📝 Generating environment configuration..."
cat > .env.production << EOF
# Environment Configuration
ENV=production
PRIMARY_PROVIDER=yahoo_finance
FALLBACK_PROVIDERS='["alpha_vantage", "web_scraper"]'
MARKET_INDEX_SYMBOL=^NSEI

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=zion_production
DB_USER=zion_production
DB_PASSWORD=$DB_PASSWORD

# Redis Configuration
REDIS_URL=redis://redis:6379

# API Keys and Secrets
YAHOO_FINANCE_API_KEY=$YAHOO_FINANCE_API_KEY
ALPHA_VANTAGE_KEY=$ALPHA_VANTAGE_KEY
FINNHUB_API_KEY=$FINNHUB_API_KEY
POLYGON_API_KEY=$POLYGON_API_KEY
API_PASS_HASH=$API_PASS_HASH
JWT_SECRET=$JWT_SECRET
GRAFANA_PASSWORD=$GRAFANA_PASSWORD

# Alert Configuration
SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL
ALERT_EMAIL=$ALERT_EMAIL
EOF

# Step 5: Start the system with production configuration
echo "🚀 Starting production system..."
docker-compose -f docker-compose.yml --env-file .env.production up -d

# Wait for system to be ready
echo "⏳ Waiting for system to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/api/health | grep -q "status.*ok"; then
        echo "✅ System is ready!"
        break
    fi
    
    echo "System not ready yet, waiting..."
    RETRY_COUNT=$((RETRY_COUNT+1))
    sleep 10
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ System failed to start within the expected time"
    docker-compose logs
    exit 1
fi

# Step 6: Run system tests to verify deployment
echo "🧪 Running system verification tests..."
./deploy/test-system.sh

if [ $? -ne 0 ]; then
    echo "❌ System verification tests failed. Rolling back deployment."
    docker-compose down
    exit 1
fi

# Step 7: Initialize market data feeds
echo "📊 Initializing market data feeds..."
source deploy/production-config.env

IFS=',' read -ra PAIRS <<< "$ALLOWED_PAIRS"

for pair in "${PAIRS[@]}"; do
    echo "🔄 Starting market feed for $pair"
    curl -X POST -H "Authorization: Bearer $(curl -s -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"'"$API_PASS"'"}' http://localhost:8000/api/auth/token | jq -r '.access_token')" \
         -H "Content-Type: application/json" \
         -d "{\"symbol\":\"$pair\",\"active\":true}" \
         http://localhost:8000/api/market/init

    # Verify data flow
    echo "Verifying market data for $pair..."
    if ! curl -s "http://localhost:8000/api/market/status/$pair" | grep -q "active"; then
        echo "❌ Market data initialization failed for $pair"
        exit 1
    fi
    
    echo "✅ $pair successfully initialized"
    sleep 5  # Stagger starts to prevent flooding
done

# Step 8: Start monitoring
echo "📈 Starting monitoring and alerting system..."
./deploy/start-metrics.sh

# Step 9: Set up emergency stop trigger
trap "echo 'Emergency shutdown triggered'; docker-compose exec backend python -c 'from backend.market import emergency_stop; emergency_stop()'" SIGINT SIGTERM

echo "✅ Zion Market Analysis Platform has been successfully deployed to production!"
echo "🌐 API is available at: http://localhost:8000/api"
echo "📊 Grafana dashboards are available at: http://localhost:3000"
echo "⚠️ Press Ctrl+C for emergency shutdown"

# Keep the script running to manage the emergency shutdown trap
tail -f /dev/null
