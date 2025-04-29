from pydantic import BaseModel, field_validator
from typing import List

class DeploymentValidation(BaseModel):
    response_time: float
    cache_hit_ratio: float
    success_rate: float
    system_metrics: dict
    security_status: dict

class SystemHealth(BaseModel):
    status: str
    details: str

class TestValidation(BaseModel):
    coverage: float
    passing_tests: float
    critical_paths_covered: bool

class DeploymentReadiness(BaseModel):
    ready: bool
    validation: DeploymentValidation
    health: SystemHealth
    test_status: TestValidation
    recommendations: List[str] = []

    @field_validator('ready')
    def validate_complete_readiness(cls, v, values):
        if not v:
            return v

        validation = values.get('validation')
        health = values.get('health')
        tests = values.get('test_status')

        # Core system checks with detailed reporting
        system_status = {
            "Performance": {
                "checks": [
                    {"name": "Response Time", "passed": validation.response_time < 2.0, "value": f"{validation.response_time:.2f}s", "threshold": "< 2.0s"},
                    {"name": "Cache Hit Ratio", "passed": validation.cache_hit_ratio >= 0.7, "value": f"{validation.cache_hit_ratio*100:.1f}%", "threshold": "≥ 70%"},
                    {"name": "Success Rate", "passed": validation.success_rate >= 95.0, "value": f"{validation.success_rate:.1f}%", "threshold": "≥ 95%"}
                ]
            },
            "Resources": {
                "checks": [
                    {"name": "CPU Usage", "passed": validation.system_metrics['cpu_usage'] < 80, "value": f"{validation.system_metrics['cpu_usage']:.1f}%", "threshold": "< 80%"},
                    {"name": "Memory Usage", "passed": validation.system_metrics['memory_usage'] < 80, "value": f"{validation.system_metrics['memory_usage']:.1f}%", "threshold": "< 80%"}
                ]
            },
            "Security": {
                "checks": [
                    {"name": "Auth Failures", "passed": validation.security_status['auth_failures'] < 100, "value": str(validation.security_status['auth_failures']), "threshold": "< 100"}
                ]
            },
            "Testing": {
                "checks": [
                    {"name": "Test Coverage", "passed": tests.coverage >= 80.0, "value": f"{tests.coverage:.1f}%", "threshold": "≥ 80%"},
                    {"name": "Passing Tests", "passed": tests.passing_tests == 100.0, "value": f"{tests.passing_tests:.1f}%", "threshold": "100%"},
                    {"name": "Critical Paths", "passed": tests.critical_paths_covered, "value": str(tests.critical_paths_covered), "threshold": "True"}
                ]
            }
        }

        failures = []

        # Collect failures for each check
        for category, details in system_status.items():
            for check in details["checks"]:
                if not check["passed"]:
                    failures.append(f"{check['name']} check under {category} failed: {check['value']} (Threshold: {check['threshold']})")

        if failures:
            raise ValueError(f"System not ready: {', '.join(failures)}")

        return v