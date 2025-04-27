#!/usr/bin/env python

import asyncio
import logging
from datetime import datetime, timedelta
import httpx  # Updated import
from backend.api.models.validation import (
    DeploymentReadiness, PerformanceMetrics, ResourceMetrics,
    OperationalMetrics, TestStatus, DependencyStatus,
    CheckCategory, MetricCheck
)
from backend.config.settings import get_settings  # Updated import

settings = get_settings()
logger = logging.getLogger(__name__)
BASE_URL = "http://example.com"  # Define BASE_URL globally (update as needed)

async def gather_metrics():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/metrics", timeout=15)  # Updated to use httpx
            response.raise_for_status()
            metrics_text = response.text
            logger.info("/metrics endpoint fetched successfully.")

        resources = ResourceMetrics()
        operational = OperationalMetrics()

        resources.cpu_usage_percent = parse_prometheus_metric(metrics_text, 'system_cpu_usage_percent')  # Updated metric
        resources.memory_usage_percent = parse_prometheus_metric(metrics_text, 'system_memory_usage_percent')  # Updated metric
        resources.disk_usage_percent = parse_prometheus_metric(metrics_text, 'system_disk_usage_percent')  # Updated metric
        operational.auth_failures = parse_prometheus_metric(metrics_text, 'auth_failures_total')  # Ensure correct metric

        return resources, operational  # Removed performance from return tuple
    except Exception as e:
        logger.error(f"Error gathering metrics: {e}")
        return None, None

async def check_readiness():
    try:
        readiness_data = {}
        test_task = asyncio.create_task(run_tests())
        metrics_task = asyncio.create_task(gather_metrics())
        deps_task = asyncio.create_task(check_dependencies())  # Added dependencies task
        perf_task = asyncio.to_thread(check_performance)  # Added performance task

        readiness_data['testing'] = await test_task
        resources_metrics, operational_metrics = await metrics_task  # Correctly unpack tuple
        readiness_data['resources'] = resources_metrics
        readiness_data['operational'] = operational_metrics
        readiness_data['dependencies'] = await deps_task
        readiness_data['performance'] = await perf_task

        # Remove timestamp and check_interval
        # readiness_data['timestamp'] = datetime.now()
        # readiness_data['check_interval'] = settings.READINESS_CHECK_INTERVAL

        # Instantiate and validate the final readiness object
        readiness_report = DeploymentReadiness(**readiness_data)
        logger.info("🏁 Market Readiness Check Complete.")
        return readiness_report
    except Exception as e:
        logger.error(f"Error checking readiness: {e}")
        return None

# Helper functions (ensure these are included)
async def run_command(command):
    pass  # ...implementation of run_command...

def parse_prometheus_metric(metrics_text, metric_name):
    pass  # ...implementation of parse_prometheus_metric...

def parse_coverage_xml(file_path):
    pass  # ...implementation of parse_coverage_xml...

def read_load_test_results(file_path):
    pass  # ...implementation of read_load_test_results...

async def check_api_health():
    pass  # ...implementation of check_api_health...

async def check_dependencies():
    pass  # ...implementation of check_dependencies...

async def run_tests():
    pass  # ...implementation of run_tests...

def check_performance():
    pass  # ...implementation of check_performance...

def print_report(report):
    pass  # ...implementation of print_report...

# Main execution block
if __name__ == "__main__":
    import sys

    async def main():
        final_report = await check_readiness()
        if final_report:
            print_report(final_report)
            sys.exit(0 if final_report.overall_ready else 1)
        else:
            logger.error("Failed to generate readiness report.")
            sys.exit(1)

    asyncio.run(main())

# Reminder: Verify the exact Prometheus metric names used in `gather_metrics` by checking the output of your application's `/metrics` endpoint.