
# backend/api/models/validation.py
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# --- Supporting Models ---

class MetricCheck(BaseModel):
    name: str
    passed: bool = False
    value: Optional[Any] = None
    threshold: Optional[str] = None
    details: Optional[str] = None # Optional extra info or error message

class CheckCategory(BaseModel):
    category_name: str
    checks: List[MetricCheck] = []
    category_passed: bool = False # Overall status for the category

    @root_validator(pre=False, skip_on_failure=True)
    def calculate_category_passed(cls, values):
        checks = values.get('checks', [])
        values['category_passed'] = all(check.passed for check in checks)
        return values

# --- Core Readiness Models ---

class PerformanceMetrics(BaseModel):
    avg_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None # 95th percentile latency
    requests_per_second: Optional[float] = None
    success_rate_percent: Optional[float] = None # From load test or monitoring

class ResourceMetrics(BaseModel):
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None # If relevant

class OperationalMetrics(BaseModel):
    cache_hit_ratio: Optional[float] = None
    error_rate_percent: Optional[float] = None # e.g., 5xx errors / total requests
    auth_failures: Optional[int] = None

class TestStatus(BaseModel):
    unit_tests_passed: bool = False
    integration_tests_passed: bool = False
    e2e_tests_passed: bool = False
    coverage_percent: Optional[float] = None
    critical_paths_covered: bool = False # Could be manually set or inferred

class DependencyStatus(BaseModel):
    redis_connection: bool = False
    primary_api_connection: bool = False # If applicable and testable
    # Add other critical dependencies (DB, etc.)

# --- Main Readiness Model ---

class DeploymentReadiness(BaseModel):
    overall_ready: bool = Field(default=False, description="Overall readiness status")
    performance: Optional[PerformanceMetrics] = None
    resources: Optional[ResourceMetrics] = None
    operational: Optional[OperationalMetrics] = None
    testing: Optional[TestStatus] = None
    dependencies: Optional[DependencyStatus] = None
    checks_summary: List[CheckCategory] = []
    recommendations: List[str] = []

    # --- Thresholds (Could be loaded from config) ---
    THRESHOLD_AVG_LATENCY_MS: float = 1000.0
    THRESHOLD_P95_LATENCY_MS: float = 2500.0
    THRESHOLD_SUCCESS_RATE_PERCENT: float = 99.0
    THRESHOLD_CPU_USAGE_PERCENT: float = 80.0
    THRESHOLD_MEMORY_USAGE_PERCENT: float = 85.0
    THRESHOLD_CACHE_HIT_RATIO: float = 0.70 # 70%
    THRESHOLD_ERROR_RATE_PERCENT: float = 1.0 # Max 1% error rate
    THRESHOLD_COVERAGE_PERCENT: float = 80.0

    @root_validator(pre=False, skip_on_failure=True)
    def perform_readiness_validation(cls, values):
        """Validates all gathered metrics against thresholds and sets overall_ready."""
        logger.info("Performing final readiness validation...")
        perf = values.get('performance')
        res = values.get('resources')
        ops = values.get('operational')
        test = values.get('testing')
        deps = values.get('dependencies')
        checks_summary: List[CheckCategory] = []
        recommendations: List[str] = []
        all_passed = True

        # Helper to add checks
        def add_check(category_list: List[CheckCategory], cat_name: str, check_name: str, is_passed: bool, val: Any, thresh: str, details: Optional[str] = None):
            category = next((c for c in category_list if c.category_name == cat_name), None)
            if not category:
                category = CheckCategory(category_name=cat_name)
                category_list.append(category)
            category.checks.append(MetricCheck(name=check_name, passed=is_passed, value=val, threshold=thresh, details=details))
            return is_passed

        # 1. Performance Checks
        cat_name = "Performance"
        if perf:
            if perf.avg_latency_ms is not None:
                passed = add_check(checks_summary, cat_name, "Avg Latency", perf.avg_latency_ms <= cls.THRESHOLD_AVG_LATENCY_MS, f"{perf.avg_latency_ms:.0f}ms", f"<= {cls.THRESHOLD_AVG_LATENCY_MS:.0f}ms")
                if not passed: all_passed = False; recommendations.append("Investigate high average latency.")
            if perf.p95_latency_ms is not None:
                 passed = add_check(checks_summary, cat_name, "P95 Latency", perf.p95_latency_ms <= cls.THRESHOLD_P95_LATENCY_MS, f"{perf.p95_latency_ms:.0f}ms", f"<= {cls.THRESHOLD_P95_LATENCY_MS:.0f}ms")
                 if not passed: all_passed = False; recommendations.append("Investigate high P95 latency (tail latency).")
            if perf.success_rate_percent is not None:
                 passed = add_check(checks_summary, cat_name, "Success Rate", perf.success_rate_percent >= cls.THRESHOLD_SUCCESS_RATE_PERCENT, f"{perf.success_rate_percent:.1f}%", f">= {cls.THRESHOLD_SUCCESS_RATE_PERCENT:.1f}%")
                 if not passed: all_passed = False; recommendations.append("Improve request success rate.")
        else:
             add_check(checks_summary, cat_name, "Metrics Available", False, "N/A", "Required", "Performance metrics missing")
             all_passed = False

        # 2. Resource Checks
        cat_name = "Resources"
        if res:
            if res.cpu_usage_percent is not None:
                 passed = add_check(checks_summary, cat_name, "CPU Usage", res.cpu_usage_percent < cls.THRESHOLD_CPU_USAGE_PERCENT, f"{res.cpu_usage_percent:.1f}%", f"< {cls.THRESHOLD_CPU_USAGE_PERCENT:.0f}%")
                 if not passed: all_passed = False; recommendations.append("Optimize CPU usage or scale resources.")
            if res.memory_usage_percent is not None:
                 passed = add_check(checks_summary, cat_name, "Memory Usage", res.memory_usage_percent < cls.THRESHOLD_MEMORY_USAGE_PERCENT, f"{res.memory_usage_percent:.1f}%", f"< {cls.THRESHOLD_MEMORY_USAGE_PERCENT:.0f}%")
                 if not passed: all_passed = False; recommendations.append("Investigate memory leaks or optimize memory usage.")
        else:
             add_check(checks_summary, cat_name, "Metrics Available", False, "N/A", "Required", "Resource metrics missing")
             all_passed = False

        # 3. Operational Checks
        cat_name = "Operational"
        if ops:
            if ops.cache_hit_ratio is not None:
                 passed = add_check(checks_summary, cat_name, "Cache Hit Ratio", ops.cache_hit_ratio >= cls.THRESHOLD_CACHE_HIT_RATIO, f"{ops.cache_hit_ratio*100:.1f}%", f">= {cls.THRESHOLD_CACHE_HIT_RATIO*100:.0f}%")
                 if not passed: all_passed = False; recommendations.append("Improve caching strategy.")
            if ops.error_rate_percent is not None:
                 passed = add_check(checks_summary, cat_name, "Error Rate", ops.error_rate_percent <= cls.THRESHOLD_ERROR_RATE_PERCENT, f"{ops.error_rate_percent:.2f}%", f"<= {cls.THRESHOLD_ERROR_RATE_PERCENT:.1f}%")
                 if not passed: all_passed = False; recommendations.append("Investigate application errors.")
            if ops.auth_failures is not None: # Example check, threshold might vary
                 passed = add_check(checks_summary, cat_name, "Auth Failures", ops.auth_failures < 100, f"{ops.auth_failures}", "< 100", "Monitor unusual auth activity")
                 # This might be informational rather than blocking
        else:
             add_check(checks_summary, cat_name, "Metrics Available", False, "N/A", "Required", "Operational metrics missing")
             all_passed = False

        # 4. Testing Checks
        cat_name = "Testing"
        if test:
            passed = add_check(checks_summary, cat_name, "Unit Tests", test.unit_tests_passed, str(test.unit_tests_passed), "True")
            if not passed: all_passed = False; recommendations.append("Fix failing unit tests.")
            passed = add_check(checks_summary, cat_name, "Integration Tests", test.integration_tests_passed, str(test.integration_tests_passed), "True")
            if not passed: all_passed = False; recommendations.append("Fix failing integration tests.")
            passed = add_check(checks_summary, cat_name, "E2E Tests", test.e2e_tests_passed, str(test.e2e_tests_passed), "True")
            if not passed: all_passed = False; recommendations.append("Fix failing E2E tests.")
            if test.coverage_percent is not None:
                 passed = add_check(checks_summary, cat_name, "Test Coverage", test.coverage_percent >= cls.THRESHOLD_COVERAGE_PERCENT, f"{test.coverage_percent:.1f}%", f">= {cls.THRESHOLD_COVERAGE_PERCENT:.0f}%")
                 if not passed: all_passed = False; recommendations.append("Increase test coverage.")
            passed = add_check(checks_summary, cat_name, "Critical Paths Covered", test.critical_paths_covered, str(test.critical_paths_covered), "True")
            if not passed: all_passed = False; recommendations.append("Ensure critical paths are covered by tests.")
        else:
             add_check(checks_summary, cat_name, "Status Available", False, "N/A", "Required", "Test status missing")
             all_passed = False

        # 5. Dependency Checks
        cat_name = "Dependencies"
        if deps:
            passed = add_check(checks_summary, cat_name, "Redis Connection", deps.redis_connection, str(deps.redis_connection), "True")
            if not passed: all_passed = False; recommendations.append("Check Redis service and connection.")
            passed = add_check(checks_summary, cat_name, "Primary API Connection", deps.primary_api_connection, str(deps.primary_api_connection), "True")
            if not passed: all_passed = False; recommendations.append("Check connection to primary data API.")
            # Add checks for other dependencies
        else:
             add_check(checks_summary, cat_name, "Status Available", False, "N/A", "Required", "Dependency status missing")
             all_passed = False

        # Final calculation for categories
        for category in checks_summary:
            category.category_passed = all(check.passed for check in category.checks)

        values['overall_ready'] = all_passed
        values['checks_summary'] = checks_summary
        values['recommendations'] = recommendations
        logger.info(f"Readiness validation complete. Overall Ready: {all_passed}")
        return values

import streamlit as st
import socket
import sys
import subprocess
import os
import argparse
import time
import logging
from contextlib import closing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_port_in_use(port):
    """Check if a port is in use with improved error handling and timeout"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)  # Add timeout for connection attempts
        try:
            # Try to bind to the port
            s.bind(('localhost', port))
            return False
        except (socket.error, OSError):
            # If binding fails, try to connect to check if port is truly in use
            try:
                s.connect(('localhost', port))
                return True
            except (socket.error, OSError):
                # If both bind and connect fail, port might be in transition
                time.sleep(0.5)  # Brief pause before final check
                try:
                    s.bind(('localhost', port))
                    return False
                except (socket.error, OSError):
                    return True

def kill_process_on_port(port):
    """Attempt to kill process using the port"""
    try:
        if sys.platform.startswith('win'):
            cmd = f'for /f "tokens=5" %a in (\'netstat -aon ^| findstr :{port}\') do taskkill /F /PID %a'
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
        else:
            cmd = f"lsof -ti tcp:{port} | xargs kill -9"
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
        time.sleep(1)  # Give process time to terminate
        return True
    except:
        return False

def wait_for_port_release(port, timeout=30):
    """Wait for port release with kill attempt"""
    start_time = time.time()
    retry_interval = 0.5
    kill_attempted = False

    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            logger.info(f"Port {port} is now available")
            return True
            
        remaining = int(timeout - (time.time() - start_time))
        
        # Try killing the process after 15 seconds of waiting
        if remaining < (timeout/2) and not kill_attempted:
            logger.warning(f"Port {port} still busy, attempting to free it...")
            kill_attempted = True
            if kill_process_on_port(port):
                logger.info("Successfully terminated process on port")
                time.sleep(1)
                continue
        
        if remaining % 5 == 0:
            logger.warning(f"Port {port} still in use. Waiting {remaining}s...")
            import gc
            gc.collect()
        
        time.sleep(retry_interval)
    
    logger.error(f"Timeout waiting for port {port}")
    return False

def find_free_port(start_port=8501, max_attempts=10):
    """Find free port with improved port range checking"""
    if start_port < 1024 or start_port > 65535:
        logger.warning(f"Invalid start port {start_port}, using default 8501")
        start_port = 8501
    
    for port in range(start_port, min(start_port + max_attempts, 65536)):
        if not is_port_in_use(port):
            logger.info(f"Found available port: {port}")
            return port
            
    return None

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=int(os.environ.get('STREAMLIT_PORT', 8501)))
    return parser.parse_args()

# Configure Streamlit page
st.set_page_config(
    page_title="Zion Application",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    try:
        st.title("Zion Application")
        
        # Basic structure with proper indentation
        if st.button("Click me"):
            st.write("Button clicked!")
        else:
            st.write("Click the button above")
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    if is_port_in_use(8501):
        logger.warning("Port 8501 is currently in use")
        logger.info("Attempting to free port 8501 (timeout: 30s)")
        if not wait_for_port_release(8501):
            logger.error("Could not free port 8501. Try: `streamlit stop` or restart your system")
            sys.exit(1)
            
    try:
        args = parse_args()
        port = find_free_port(start_port=args.port)
        
        if port is None:
            logger.error(f"Could not find an available port starting from {args.port}")
            sys.exit(1)
            
        logger.info(f"Starting Streamlit on port {port}")
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "--server.port", str(port),
            "--server.address", "localhost",
            "--server.headless", "true",
            sys.argv[0]
        ]
        
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
