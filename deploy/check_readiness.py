#!/usr/bin/env python3
"""
Deployment validation script for Zion Market Analysis Platform.
This script checks if all required services are running and accessible.
"""
import argparse
import json
import sys
import time
import requests
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("deployment-validator")

class DeploymentValidator:
    def __init__(self, base_url, timeout=5, max_retries=12, retry_interval=5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.failures = []

    def validate_api_availability(self):
        """Check if the API is reachable"""
        logger.info("Checking API availability...")
        try:
            response = requests.get(self.base_url, timeout=self.timeout)
            response.raise_for_status()
            logger.info(f"✅ API is available. Status: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"❌ API is not available: {str(e)}")
            self.failures.append(f"API availability check failed: {str(e)}")
            return False

    def validate_health_endpoint(self):
        """Check if the health endpoint returns a healthy status"""
        logger.info("Checking health endpoint...")
        try:
            health_url = urljoin(self.base_url, "/api/v1/health")
            response = requests.get(health_url, timeout=self.timeout)
            response.raise_for_status()
            health_data = response.json()
            
            if health_data.get("status") == "healthy":
                logger.info("✅ Health check passed")
                logger.info(f"   Database status: {health_data.get('services', {}).get('database', {}).get('status', 'unknown')}")
                logger.info(f"   Redis status: {health_data.get('services', {}).get('redis', {}).get('status', 'unknown')}")
                return True
            else:
                logger.warning(f"❌ Health check returned non-healthy status: {health_data.get('status')}")
                self.failures.append(f"Health check failed with status: {health_data.get('status')}")
                return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            self.failures.append(f"Health check failed: {str(e)}")
            return False

    def validate_metrics_endpoint(self):
        """Check if the metrics endpoint is accessible"""
        logger.info("Checking metrics endpoint...")
        try:
            metrics_url = urljoin(self.base_url, "/api/v1/metrics")
            response = requests.get(metrics_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Prometheus metrics are plain text
            if response.text and "zion_" in response.text:
                logger.info("✅ Metrics endpoint is accessible")
                return True
            else:
                logger.warning("❌ Metrics endpoint returned unexpected data")
                self.failures.append("Metrics endpoint returned unexpected data")
                return False
        except Exception as e:
            logger.error(f"❌ Metrics check failed: {str(e)}")
            self.failures.append(f"Metrics check failed: {str(e)}")
            return False

    def validate_docs_endpoint(self):
        """Check if API documentation is accessible"""
        logger.info("Checking API documentation...")
        try:
            docs_url = urljoin(self.base_url, "/api/docs")
            response = requests.get(docs_url, timeout=self.timeout)
            response.raise_for_status()
            
            if "swagger" in response.text.lower():
                logger.info("✅ API documentation is accessible")
                return True
            else:
                logger.warning("❌ API documentation returned unexpected content")
                self.failures.append("API documentation returned unexpected content")
                return False
        except Exception as e:
            logger.error(f"❌ API documentation check failed: {str(e)}")
            self.failures.append(f"API documentation check failed: {str(e)}")
            return False

    def run_all_validations(self, wait_for_readiness=False):
        """Run all validation checks"""
        if wait_for_readiness:
            logger.info(f"Waiting for services to become ready (max {self.max_retries * self.retry_interval} seconds)...")
            for attempt in range(1, self.max_retries + 1):
                logger.info(f"Attempt {attempt}/{self.max_retries}...")
                if self.validate_api_availability():
                    break
                if attempt < self.max_retries:
                    logger.info(f"Waiting {self.retry_interval} seconds before next attempt...")
                    time.sleep(self.retry_interval)
            else:
                logger.error("Max retries reached. API is not available.")
                return False
        else:
            if not self.validate_api_availability():
                return False
        
        # Reset failures before running other validations
        self.failures = []
        
        # Run all other validations
        health_ok = self.validate_health_endpoint()
        metrics_ok = self.validate_metrics_endpoint()
        docs_ok = self.validate_docs_endpoint()
        
        all_passed = all([health_ok, metrics_ok, docs_ok])
        
        if all_passed:
            logger.info("🎉 All validation checks passed! Deployment is ready.")
            return True
        else:
            logger.error("⚠️ Some validation checks failed:")
            for i, failure in enumerate(self.failures, 1):
                logger.error(f"  {i}. {failure}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Validate Zion Market Analysis Platform deployment")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the deployed API")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout in seconds")
    parser.add_argument("--wait", action="store_true", help="Wait for services to become ready")
    parser.add_argument("--max-retries", type=int, default=12, help="Maximum number of retry attempts when waiting")
    parser.add_argument("--retry-interval", type=int, default=5, help="Seconds to wait between retry attempts")
    
    args = parser.parse_args()
    
    validator = DeploymentValidator(
        base_url=args.base_url,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_interval=args.retry_interval
    )
    
    success = validator.run_all_validations(wait_for_readiness=args.wait)
    
    # Exit with appropriate code for CI/CD pipelines
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()