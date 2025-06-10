#!/bin/bash

# 🚀 Zion Market Analysis Platform - Production Deployment Script
# This script handles the complete deployment process for production

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="zion-market-analysis"
DOCKER_IMAGE="$PROJECT_NAME:latest"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if required environment files exist
    if [[ ! -f "api_keys.env" ]]; then
        log_error "api_keys.env file not found. Please create it with required API keys."
        exit 1
    fi
    
    if [[ ! -f "deploy/staging-config.env" ]]; then
        log_error "deploy/staging-config.env file not found."
        exit 1
    fi
    
    # Check if tests are passing
    log_info "Running test suite..."
    if ! python -m pytest tests/ -v --tb=short; then
        log_error "Tests are failing. Please fix them before deployment."
        exit 1
    fi
    
    log_success "Pre-deployment checks passed!"
}

# Backup current state
backup_current_state() {
    log_info "Creating backup of current state..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup database if running
    if docker ps | grep -q postgres; then
        log_info "Backing up database..."
        docker exec $(docker ps | grep postgres | awk '{print $1}') \
            pg_dump -U zion_production zion_production > "$BACKUP_DIR/database_backup.sql"
    fi
    
    # Backup logs
    if [[ -d "logs" ]]; then
        cp -r logs "$BACKUP_DIR/"
    fi
    
    # Backup configuration
    cp -r deploy "$BACKUP_DIR/"
    
    log_success "Backup created at $BACKUP_DIR"
}

# Build and test Docker image
build_and_test() {
    log_info "Building Docker image..."
    
    docker build -t "$DOCKER_IMAGE" .
    
    log_info "Testing Docker image..."
    
    # Run a quick smoke test
    docker run --rm \
        -e DATABASE_URL="sqlite:///test.db" \
        -e REDIS_URL="redis://localhost:6379" \
        "$DOCKER_IMAGE" \
        python -c "
import sys
sys.path.append('/app')
from backend.api.main import app
print('✅ Application imports successfully')
"
    
    log_success "Docker image built and tested successfully!"
}

# Deploy to staging
deploy_staging() {
    log_info "Deploying to staging environment..."
    
    # Stop existing staging containers
    docker-compose -f docker-compose.staging.yml down
    
    # Start staging environment
    docker-compose -f docker-compose.staging.yml up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
        log_success "Staging deployment successful! Health check passed."
    else
        log_error "Staging deployment failed! Health check failed."
        exit 1
    fi
}

# Deploy to production
deploy_production() {
    log_info "Deploying to production environment..."
    
    # Stop existing production containers gracefully
    docker-compose down
    
    # Deploy with production configuration
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for production services to be ready..."
    sleep 60
    
    # Health check
    local health_check_url="${PRODUCTION_URL:-http://localhost:8000}/api/health"
    if curl -f "$health_check_url" >/dev/null 2>&1; then
        log_success "Production deployment successful! Health check passed."
    else
        log_error "Production deployment failed! Health check failed."
        log_info "Rolling back to previous version..."
        rollback
        exit 1
    fi
}

# Rollback function
rollback() {
    log_warning "Rolling back deployment..."
    
    # Stop current containers
    docker-compose down
    
    # Restore from backup if available
    if [[ -d "$BACKUP_DIR" ]]; then
        # Restore database
        if [[ -f "$BACKUP_DIR/database_backup.sql" ]]; then
            log_info "Restoring database..."
            docker-compose up -d postgres
            sleep 10
            docker exec -i $(docker ps | grep postgres | awk '{print $1}') \
                psql -U zion_production zion_production < "$BACKUP_DIR/database_backup.sql"
        fi
    fi
    
    log_warning "Rollback completed. Please investigate the issue."
}

# Post-deployment tasks
post_deployment() {
    log_info "Running post-deployment tasks..."
    
    # Run database migrations if needed
    log_info "Running database migrations..."
    docker-compose exec backend alembic upgrade head
    
    # Clear cache
    log_info "Clearing cache..."
    docker-compose exec redis redis-cli FLUSHALL
    
    # Send deployment notification (if configured)
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"🚀 Zion Market Analysis Platform deployed successfully!"}' \
            "$SLACK_WEBHOOK_URL"
    fi
    
    log_success "Post-deployment tasks completed!"
}

# Main deployment function
main() {
    echo "========================================"
    echo "🚀 Zion Market Analysis Platform"
    echo "Production Deployment Script"
    echo "========================================"
    
    local deployment_type="${1:-staging}"
    
    case "$deployment_type" in
        "staging")
            log_info "Starting staging deployment..."
            pre_deployment_checks
            backup_current_state
            build_and_test
            deploy_staging
            post_deployment
            ;;
        "production")
            log_info "Starting production deployment..."
            log_warning "This will deploy to PRODUCTION environment!"
            read -p "Are you sure you want to continue? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                pre_deployment_checks
                backup_current_state
                build_and_test
                deploy_production
                post_deployment
            else
                log_info "Deployment cancelled."
                exit 0
            fi
            ;;
        "rollback")
            rollback
            ;;
        *)
            echo "Usage: $0 {staging|production|rollback}"
            echo ""
            echo "Examples:"
            echo "  $0 staging     - Deploy to staging environment"
            echo "  $0 production  - Deploy to production environment"
            echo "  $0 rollback    - Rollback to previous version"
            exit 1
            ;;
    esac
    
    log_success "Deployment completed successfully! 🎉"
    log_info "Monitor the application at: ${PRODUCTION_URL:-http://localhost:8000}"
    log_info "Check metrics at: ${METRICS_URL:-http://localhost:9090}"
}

# Trap errors and provide cleanup
trap 'log_error "Deployment failed! Check the logs above for details."' ERR

# Run main function with all arguments
main "$@"
