# Zion Market Analysis Platform

A sophisticated market analysis system combining multiple data sources, AI agents, and real-time monitoring.

## Features

- Multi-agent analysis system
- Real-time market data processing
- AI-powered insights
- Production-grade security
- Comprehensive monitoring

## Quick Start

1. Environment Setup:
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Configuration:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

3. Run Development Server:
```bash
uvicorn backend.api.main:app --reload
```

## Architecture

```
backend/
├── agents/          # Analysis agents
├── api/            # FastAPI endpoints
├── core/           # Core business logic
├── monitoring/     # Metrics and monitoring
└── utils/          # Shared utilities
```

## Security

- JWT authentication required for all endpoints
- Rate limiting per user
- Input validation
- Secure secret management

## Monitoring

Access metrics at `/metrics` endpoint:
- System health
- Analysis performance
- Agent execution stats
- Cache hit rates

## API Documentation

Swagger UI available at `/docs`

## Environment Variables

Required environment variables:
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `ALPHA_VANTAGE_KEY`: Alpha Vantage API key
- `REDIS_URL`: Redis connection URL

## Testing

Run tests:
```bash
pytest
```

Load testing:
```bash
locust -f tests/load/locustfile.py
```
