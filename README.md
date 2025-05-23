# Zion Market Analysis Platform

## Overview
The Zion Market Analysis Platform is a comprehensive toolkit for advanced market analysis, portfolio optimization, and strategic investment decision-making. It leverages multiple data sources and employs sophisticated analytical algorithms to deliver actionable insights.

## Features
- Real-time market data integration from multiple sources
- Technical analysis (RSI, MACD, Bollinger Bands, etc.)
- Fundamental analysis (PE ratio, EPS, PB ratio, etc.)
- Sentiment analysis from news and social media
- ESG scoring and analysis
- Portfolio optimization and risk assessment
- Backtesting capabilities for strategy validation
- Interactive dashboards and visualization
- Alert system for market events

## Architecture
The platform consists of:
- FastAPI backend for data processing and analysis
- React frontend for visualization and user interaction
- PostgreSQL database for data persistence
- Redis for caching and performance optimization
- Prometheus and Grafana for monitoring
- Docker containers for deployment consistency

## Prerequisites
- Docker and Docker Compose
- API keys for data providers (Alpha Vantage, Yahoo Finance, etc.)
- Minimum 4GB RAM and 2 CPU cores for optimal performance

## Quick Start Deployment

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/zion.git
cd zion
```

### 2. Set up environment variables
Create a `.env` file in the root directory with the following variables:
```
JWT_SECRET_KEY=your-secure-jwt-key
POSTGRES_PASSWORD=your-db-password
REDIS_PASSWORD=your-redis-password
GRAFANA_PASSWORD=your-grafana-admin-password
ALPHA_VANTAGE_KEY=your-alpha-vantage-api-key
# Add other API keys as needed
```

### 3. Build and deploy with Docker Compose
```bash
docker-compose up -d
```

### 4. Access the application
- Frontend: http://localhost (or your server's IP/domain)
- API documentation: http://localhost/api/docs
- Grafana dashboards: http://localhost:3000 (admin/your-grafana-password)

## Production Deployment

For production environments, additional steps are recommended:

### 1. Secure secrets management
Use a secrets manager or environment variables securely injected into containers.

### 2. Set up SSL/TLS
Modify the nginx configuration to enable HTTPS with proper certificates.

### 3. Configure backup strategy
Set up regular database backups using the scripts in `/deploy/backup-scripts/`.

### 4. Scale services as needed
The docker-compose file includes resource limits that can be adjusted based on your workload requirements.

### 5. Enable monitoring alerts
Configure Grafana alerting to notify you of system issues or market events.

## Troubleshooting

### Service health checks
All services include health checks. You can view their status with:
```bash
docker-compose ps
```

### Viewing logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
```

### Common issues
- **Database connection errors**: Check PostgreSQL is running and DATABASE_URL is correct
- **API data issues**: Verify your API keys are valid and not rate-limited
- **Frontend not loading**: Check nginx logs and ensure the build process completed successfully

## Maintenance

### Updating the platform
```bash
git pull
docker-compose down
docker-compose up -d --build
```

### Database migrations
```bash
docker-compose exec backend alembic upgrade head
```

## License
[Specify your license here]

## Support
For support inquiries, please [contact details].