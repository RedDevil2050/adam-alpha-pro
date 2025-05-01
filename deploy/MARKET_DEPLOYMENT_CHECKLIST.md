# Zion Market Analysis Platform - Production Deployment Checklist

## Pre-Deployment Checks

### Azure Resources

- [ ] Azure Key Vault "zion-production-kv" has been created

- [ ] All required secrets have been added to Key Vault:
  - [ ] DbPassword
  - [ ] GrafanaPassword
  - [ ] JwtSecret
  - [ ] ApiPassHash
  - [ ] AlphaVantageKey
  - [ ] YahooFinanceApiKey
  - [ ] FinnhubApiKey
  - [ ] PolygonApiKey
  - [ ] SlackWebhookUrl
  - [ ] AlertEmail

- [ ] Azure CLI is installed and configured

- [ ] Azure account has proper permissions to access Key Vault

### Environment Configuration

- [ ] Production database schema is finalized

- [ ] Production API rate limits are properly configured

- [ ] Market hours configuration is validated for target markets

- [ ] Monitoring thresholds are set to appropriate levels

### Security

- [ ] All API keys are valid and have appropriate rate limits

- [ ] JWT Secret is a secure, high-entropy value

- [ ] Database passwords meet complexity requirements

- [ ] API authentication is properly tested

- [ ] HTTPS certificates are prepared (if deploying publicly)

### Infrastructure

- [ ] Docker is installed and running

- [ ] Docker Compose is installed

- [ ] Docker resources (CPU/memory) are sufficient

- [ ] Database backup system is configured

- [ ] Sufficient disk space is available

- [ ] Network access allows all required ports

### Monitoring & Alerting

- [ ] Prometheus is configured with appropriate scrape intervals

- [ ] Grafana dashboards are finalized

- [ ] Alert thresholds are properly set

- [ ] Slack webhook URLs are valid

- [ ] Email notification system is tested

### Data Integrity

- [ ] Initial market data quality is verified

- [ ] Fallback providers are configured and tested

- [ ] Historical data is loaded (if required)

- [ ] Data caching is properly configured

### Operational Readiness

- [ ] Emergency shutdown procedure is documented and tested

- [ ] Backup and restore procedures are documented and tested

- [ ] Support contact information is current

- [ ] SLAs are established and documented

- [ ] On-call schedule is established (if applicable)

## Deployment Steps

1. Execute market deployment script:
   - On Windows: `.\deploy\market-launch.ps1`
   - On Linux/Mac: `./deploy/market-launch.sh`

2. Verify system status:
   - [ ] All services are running
   - [ ] API health endpoint returns status "ok"
   - [ ] Market data is flowing
   - [ ] Monitoring system is receiving metrics

3. Run post-deployment verification:
   - [ ] Test API endpoints
   - [ ] Verify data quality
   - [ ] Check monitoring dashboards
   - [ ] Test alert notifications

## Post-Deployment

- [ ] Monitor system for 24 hours

- [ ] Verify data quality across all market hours

- [ ] Test emergency shutdown and recovery

- [ ] Document any issues and resolutions

## Emergency Contacts

- Primary: [Name] - [Contact Info]
- Secondary: [Name] - [Contact Info]
- Technical Lead: [Name] - [Contact Info]

## Last Updated

May 1, 2025
