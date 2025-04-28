#!/usr/bin/env python

import asyncio
import logging
import httpx
from backend.api.models.validation import (
    DeploymentReadiness, PerformanceMetrics, ResourceMetrics,
    OperationalMetrics, TestStatus, DependencyStatus,
)
from backend.config.settings import get_settings
import sys
import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional
import re
from datetime import datetime

# Add the backend module to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

settings = get_settings()
logger = logging.getLogger(__name__)

project_root = Path(__file__).resolve().parent.parent.parent  # Adjusted to point to the correct root
BASE_URL = "http://localhost:8000"
TEST_COMMAND_UNIT = "pytest tests/unit"
TEST_COMMAND_INTEGRATION = "pytest tests/integration"
TEST_COMMAND_E2E = "pytest tests/e2e"
COVERAGE_COMMAND = "pytest --cov=./backend --cov-report xml:coverage.xml -n auto"
COVERAGE_FILE = project_root / "coverage.xml"
LOAD_TEST_RESULT_FILE = project_root / "load_test_results.json"

# Configure logging with timestamps and log levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Dynamic configuration for thresholds and metric names
CPU_USAGE_THRESHOLD = float(os.getenv("CPU_USAGE_THRESHOLD", 80.0))
MEMORY_USAGE_THRESHOLD = float(os.getenv("MEMORY_USAGE_THRESHOLD", 80.0))
DISK_USAGE_THRESHOLD = float(os.getenv("DISK_USAGE_THRESHOLD", 90.0))
AUTH_FAILURES_THRESHOLD = int(os.getenv("AUTH_FAILURES_THRESHOLD", 10))

async def gather_metrics():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/metrics", timeout=15)
            response.raise_for_status()
            metrics_text = response.text
            logger.info("/metrics endpoint fetched successfully.")

        resources = ResourceMetrics()
        operational = OperationalMetrics()

        resources.cpu_usage_percent = parse_prometheus_metric(metrics_text, 'system_cpu_usage_percent')
        resources.memory_usage_percent = parse_prometheus_metric(metrics_text, 'system_memory_usage_percent')
        resources.disk_usage_percent = parse_prometheus_metric(metrics_text, 'system_disk_usage_percent')
        operational.auth_failures = parse_prometheus_metric(metrics_text, 'auth_failures_total')

        return resources, operational
    except Exception as e:
        logger.error(f"Error gathering metrics: {e}")
        return None, None

async def check_readiness():
    try:
        readiness_data = {}
        async with httpx.AsyncClient() as client:
            test_task = asyncio.create_task(run_tests())
            metrics_task = asyncio.create_task(gather_metrics())
            deps_task = asyncio.create_task(check_dependencies(client))
            perf_task = asyncio.to_thread(check_performance)

            readiness_data['testing'] = await test_task
            resources_metrics, operational_metrics = await metrics_task
            readiness_data['resources'] = resources_metrics
            readiness_data['operational'] = operational_metrics
            readiness_data['dependencies'] = await deps_task
            readiness_data['performance'] = await perf_task

        readiness_report = DeploymentReadiness(**readiness_data)
        logger.info("Market Readiness Check Complete.")
        return readiness_report
    except Exception as e:
        logger.error(f"Error checking readiness: {e}")
        return None

async def run_command(command):
    logger.info(f"Running command: {command}")
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if stdout:
        logger.info(f"Command output: {stdout.decode()}")
    if stderr:
        logger.error(f"Command error: {stderr.decode()}")
    return process.returncode, stdout.decode(), stderr.decode()

def parse_prometheus_metric(metrics_text: str, metric_name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
    """Parses a simple gauge or counter value from Prometheus text format."""
    label_str = ""
    if labels:
        label_parts = [f'{k}="{v}"' for k, v in labels.items()]
        label_str = "{" + ",".join(label_parts) + "}"

    pattern_str = rf"^{metric_name}"
    if label_str:
        pattern_str += r"\{.*" + re.escape(label_str.strip('{}')) + r".*\}"
    pattern_str += r"\s+([\d\.\+\-eE]+)"

    pattern = re.compile(pattern_str, re.MULTILINE)
    match = pattern.search(metrics_text)

    if match:
        try:
            return float(match.group(1))
        except ValueError:
            logger.warning(f"Could not parse value for metric {metric_name}: {match.group(1)}")
            return None
    label_info = f" with labels {labels}" if labels else ""
    logger.warning(f"Metric {metric_name}{label_info} not found in metrics output.")
    return None

def parse_coverage_xml(file_path: Path) -> Optional[float]:
    """Parses coverage percentage from coverage.xml."""
    if not file_path.is_file():
        logger.error(f"Coverage file not found: {file_path}")
        return None
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        line_rate = root.get('line-rate')
        if line_rate:
            return float(line_rate) * 100
        logger.warning("Could not find 'line-rate' attribute in coverage.xml root.")
        return None
    except Exception as e:
        logger.error(f"Error parsing coverage file {file_path}: {e}")
        return None

def read_load_test_results(file_path: Path) -> Optional[Dict[str, Any]]:
    """Reads load test results from a JSON file."""
    if not file_path.is_file():
        logger.warning(f"Load test result file not found: {file_path}")
        return None
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading load test results {file_path}: {e}")
        return None

async def check_dependencies(client: httpx.AsyncClient) -> DependencyStatus:
    """Checks critical dependencies (e.g., Redis via health endpoint detail)."""
    status = DependencyStatus()
    try:
        # Assuming /health provides detailed dependency status
        response = await client.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            details = response.json()
            # Adjust keys based on your actual /health response structure
            status.redis_connection = details.get("dependencies", {}).get("redis") == "ok"
            status.primary_api_connection = details.get("dependencies", {}).get("primary_api") == "ok" # Example
            logger.info(f"Dependency check via /health: Redis={status.redis_connection}, PrimaryAPI={status.primary_api_connection}")
        else:
             logger.warning(f"Could not get detailed dependency status from /health (Status: {response.status_code})")

    except Exception as e:
        logger.error(f"Error checking dependencies via /health: {e}")

    # Fallback: Direct Redis check
    try:
        import redis.asyncio as aioredis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis = await aioredis.from_url(redis_url)
        await redis.ping()
        status.redis_connection = True
        await redis.close()
        logger.info("Direct Redis ping successful.")
    except Exception as redis_err:
        logger.error(f"Direct Redis ping failed: {redis_err}")
        status.redis_connection = False

    return status

async def run_tests() -> TestStatus:
    """Runs unit, integration, and E2E tests and gathers coverage."""
    status = TestStatus()
    logger.info("--- Running Tests ---")

    # Run test suites
    unit_success, _, _ = await run_command(TEST_COMMAND_UNIT)
    status.unit_tests_passed = unit_success == 0

    integration_success, _, _ = await run_command(TEST_COMMAND_INTEGRATION)
    status.integration_tests_passed = integration_success == 0

    e2e_success, _, _ = await run_command(TEST_COMMAND_E2E)
    status.e2e_tests_passed = e2e_success == 0

    # Run coverage
    cov_success, cov_stdout, cov_stderr = await run_command(COVERAGE_COMMAND)
    if cov_success == 0 or "coverage: platform" in cov_stderr: # Command might exit non-zero but still generate report
        status.coverage_percent = parse_coverage_xml(COVERAGE_FILE)
    else:
        logger.error("Coverage command failed to execute properly.")

    # Critical paths - often a manual check or based on specific test tags/markers
    # Simplistic assumption: E2E covers critical paths if they pass
    status.critical_paths_covered = status.e2e_tests_passed

    logger.info(f"Test Results: Unit={status.unit_tests_passed}, Integration={status.integration_tests_passed}, E2E={status.e2e_tests_passed}, Coverage={status.coverage_percent}%, CriticalPaths={status.critical_paths_covered}")
    return status

def check_performance() -> Optional[PerformanceMetrics]:
    """Checks performance based on load test results."""
    # This part is highly dependent on your load testing tool and output format
    logger.info("--- Checking Performance from Load Tests ---")
    load_results = read_load_test_results(LOAD_TEST_RESULT_FILE) # Use the correct read_load_test_results
    if not load_results:
        logger.warning("Could not read load test results. Skipping performance checks.")
        return None

    perf = PerformanceMetrics()
    # Adapt keys based on your load_test_results.json structure
    # Example keys from common tools like Locust:
    perf.avg_latency_ms = load_results.get('stats', [{}])[0].get('avg_response_time')
    # For P95, Locust often stores it in stats[0]['response_times'] as a dict {0.95: value}
    p95_value = load_results.get('stats', [{}])[0].get('response_times', {}).get(0.95)
    perf.p95_latency_ms = p95_value if p95_value is not None else load_results.get('p95_latency_ms') # Fallback

    perf.requests_per_second = load_results.get('stats', [{}])[0].get('total_rps') or load_results.get('requests_per_second')

    total_reqs = load_results.get('stats', [{}])[0].get('num_requests', 0)
    failed_reqs = load_results.get('stats', [{}])[0].get('num_failures', 0)
    if total_reqs > 0:
        perf.success_rate_percent = ((total_reqs - failed_reqs) / total_reqs) * 100
    else:
        perf.success_rate_percent = 0.0

    logger.info(f"Load Test Performance: AvgLatency={perf.avg_latency_ms}ms, P95Latency={perf.p95_latency_ms}ms, RPS={perf.requests_per_second}, SuccessRate={perf.success_rate_percent}%")
    return perf

def print_report(report: DeploymentReadiness):
    """Prints a formatted readiness report to the console."""
    print("\n" + "="*60)
    print("          ZION MARKET READINESS REPORT")
    print("="*60)
    status = "✅ READY" if report.overall_ready else "❌ NOT READY"
    print(f"\nOverall Status: {status}\n")

    # Use the checks_summary generated by the DeploymentReadiness validator
    if report.checks_summary:
        for category in report.checks_summary:
            cat_status = "✅" if category.category_passed else "❌"
            print(f"\n--- {category.category_name} [{cat_status}] ---")
            for check in category.checks:
                check_status = "✅" if check.passed else "❌"
                value_str = f"Value: {check.value}" if check.value is not None else ""
                thresh_str = f"(Threshold: {check.threshold})" if check.threshold else ""
                details_str = f"- {check.details}" if check.details else ""
                print(f"  [{check_status}] {check.name:<25} {value_str:<25} {thresh_str:<20} {details_str}")
    else:
        print("\n--- Detailed Checks ---")
        print("  (No detailed check summary available - validation might have failed early)")
        # Fallback to printing raw data if checks_summary is empty
        if report.testing:
            print(f"  Testing: Unit={report.testing.unit_tests_passed}, Integration={report.testing.integration_tests_passed}, E2E={report.testing.e2e_tests_passed}, Coverage={report.testing.coverage_percent}%")
        if report.resources:
            print(f"  Resources: CPU={report.resources.cpu_usage_percent}%, Memory={report.resources.memory_usage_percent}%")
        if report.operational:
            print(f"  Operational: CacheHit={report.operational.cache_hit_ratio}, Errors={report.operational.error_rate_percent}%, AuthFails={report.operational.auth_failures}")
        if report.dependencies:
            print(f"  Dependencies: Redis={report.dependencies.redis_connection}, PrimaryAPI={report.dependencies.primary_api_connection}")
        if report.performance:
            print(f"  Performance: AvgLatency={report.performance.avg_latency_ms}ms, P95Latency={report.performance.p95_latency_ms}ms, Success={report.performance.success_rate_percent}%")

    if report.recommendations:
        print("\n--- Recommendations ---")
        for rec in report.recommendations:
            print(f"  - {rec}")

    print("\n" + "="*60)

# Reminder: Verify the Prometheus metric names used in the `gather_metrics` function
# (e.g., system_cpu_usage_percent, auth_failures_total) against the actual output
# of your application's /metrics endpoint.