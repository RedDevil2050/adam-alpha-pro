import os
import asyncio
import sys
import platform
from pathlib import Path
from loguru import logger
from backend.utils.cache_utils import get_redis_client
from backend.startup import initialize_system

async def check_redis():
    try:
        # Get Redis client instance
        redis_client = await get_redis_client()
        # Check connectivity
        pong = await redis_client.ping()
        return pong
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        return False

async def check_api():
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"API check failed: {e}")
        return False

async def check_database():
    try:
        # Import here to avoid circular imports
        from backend.db.session import AsyncSessionLocal, get_db
        
        # Get a database session
        async for session in get_db():
            # Execute a simple query to verify connectivity
            result = await session.execute("SELECT 1")
            return True
            
    except ImportError as e:
        logger.error(f"Failed to import database modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False

async def check_docker():
    try:
        proc = await asyncio.create_subprocess_shell(
            "docker ps",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error(f"Docker check failed: {stderr.decode()}")
            return False
        return True
    except Exception as e:
        logger.error(f"Docker service check failed: {e}")
        return False

async def check_azure_resources():
    """
    Verify Azure resources according to Azure best practices
    """
    try:
        import json
        # Check if the Azure CLI is installed and we have an active login
        proc = await asyncio.create_subprocess_shell(
            "az account show",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.warning("Azure CLI not available or not logged in")
            return False
            
        # Get subscription details
        account_info = json.loads(stdout.decode())
        subscription_id = account_info.get('id')
        tenant_id = account_info.get('tenantId')
        
        logger.info(f"Connected to Azure subscription: {account_info.get('name')} (ID: {subscription_id})")
        
        # Check for specific resource groups
        rg_name = os.environ.get("AZURE_RESOURCE_GROUP", "zion-resources")
        proc = await asyncio.create_subprocess_shell(
            f"az group show --name {rg_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error(f"Azure resource group '{rg_name}' not found or inaccessible")
            logger.debug(f"Error: {stderr.decode()}")
            return False
        
        # Check specific Azure resources based on deployment type
        azure_checks = []
        
        # Check Azure App Service if used
        if os.environ.get("USE_AZURE_APP_SERVICE", "false").lower() == "true":
            app_name = os.environ.get("AZURE_APP_NAME", "zion-app")
            azure_checks.append(
                asyncio.create_subprocess_shell(
                    f"az webapp show --name {app_name} --resource-group {rg_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            )
        
        # Check Azure Container Registry if used
        if os.environ.get("USE_AZURE_CONTAINER_REGISTRY", "false").lower() == "true":
            acr_name = os.environ.get("AZURE_ACR_NAME", "zionregistry")
            azure_checks.append(
                asyncio.create_subprocess_shell(
                    f"az acr show --name {acr_name} --resource-group {rg_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            )
        
        # Check Azure Storage if used
        if os.environ.get("USE_AZURE_STORAGE", "false").lower() == "true":
            storage_name = os.environ.get("AZURE_STORAGE_ACCOUNT", "zionstorage")
            azure_checks.append(
                asyncio.create_subprocess_shell(
                    f"az storage account show --name {storage_name} --resource-group {rg_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            )

        # Check Azure Key Vault if used
        if os.environ.get("USE_AZURE_KEYVAULT", "false").lower() == "true":
            vault_name = os.environ.get("AZURE_KEYVAULT_NAME", "zionvault")
            azure_checks.append(
                asyncio.create_subprocess_shell(
                    f"az keyvault show --name {vault_name} --resource-group {rg_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            )
        
        # Check Azure Cognitive Services if used
        if os.environ.get("USE_AZURE_COGNITIVE", "false").lower() == "true":
            cognitive_name = os.environ.get("AZURE_COGNITIVE_NAME", "zioncognitive")
            azure_checks.append(
                asyncio.create_subprocess_shell(
                    f"az cognitiveservices account show --name {cognitive_name} --resource-group {rg_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            )
        
        # Execute all Azure resource checks
        if azure_checks:
            procs = await asyncio.gather(*azure_checks)
            results = await asyncio.gather(*[p.communicate() for p in procs])
            
            # Check if any checks failed
            resource_types = ["App Service", "Container Registry", "Storage", "Key Vault", "Cognitive Services"]
            for i, (stdout, stderr) in enumerate(results):
                if procs[i].returncode != 0:
                    if i < len(resource_types):
                        resource_type = resource_types[i]
                        logger.error(f"Azure {resource_type} check failed: {stderr.decode()}")
                    else:
                        logger.error(f"Azure resource check #{i+1} failed: {stderr.decode()}")
                    return False
        
        logger.success("All Azure resource checks passed")
        return True
    except Exception as e:
        logger.error(f"Azure resources check failed: {e}")
        return False

async def check_disk_space():
    """Check if there's enough disk space for operations"""
    try:
        import shutil
        
        # Get disk usage statistics for the current directory
        total, used, free = shutil.disk_usage(".")
        
        # Convert to GB for readable output
        free_gb = free / (1024 ** 3)
        total_gb = total / (1024 ** 3)
        percent_free = (free / total) * 100
        
        logger.info(f"Disk space: {free_gb:.2f}GB free out of {total_gb:.2f}GB ({percent_free:.1f}%)")
        
        # Return False if less than 1GB free or less than 5% free space
        if free_gb < 1 or percent_free < 5:
            logger.error(f"Disk space critically low: {free_gb:.2f}GB free ({percent_free:.1f}%)")
            return False
        return True
    except Exception as e:
        logger.error(f"Disk space check failed: {e}")
        return False

async def check_gpu_availability():
    """Check if GPUs are available if required for ML operations"""
    try:
        # Skip if torch is not installed - it's optional
        try:
            # Check if torch is installed first
            import importlib.util
            if importlib.util.find_spec("torch") is None:
                logger.info("PyTorch not installed - skipping GPU check")
                return True
                
            import torch
            has_gpu = torch.cuda.is_available()
            if has_gpu:
                device_count = torch.cuda.device_count()
                device_names = [torch.cuda.get_device_name(i) for i in range(device_count)]
                logger.info(f"Found {device_count} GPU(s): {', '.join(device_names)}")
            else:
                logger.info("No GPUs detected")
            return True
        except ImportError:
            logger.info("PyTorch not installed - skipping GPU check")
            return True
    except Exception as e:
        logger.warning(f"GPU check failed: {e}")
        return True  # Non-critical check

def check_config_files():
    required_files = [
        "deploy/production-config.env",
        "requirements.txt",
        "docker-compose.yml"
    ]
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        logger.error(f"Missing configuration files: {missing_files}")
        return False
    return True

def check_system_requirements():
    """
    Check if the system meets the minimum requirements for running Zion
    """
    try:
        # Check Python version
        python_version = sys.version_info
        min_python_version = (3, 8)
        if python_version < min_python_version:
            logger.error(f"Python version {python_version.major}.{python_version.minor} is below minimum required version {min_python_version[0]}.{min_python_version[1]}")
            return False
        
        # Check available RAM
        import psutil
        total_ram = psutil.virtual_memory().total / (1024**3)  # GB
        if total_ram < 4:
            logger.error(f"System has {total_ram:.2f}GB RAM, minimum required is 4GB")
            return False
            
        # Check CPU cores
        cpu_count = os.cpu_count()
        if cpu_count < 2:
            logger.error(f"System has {cpu_count} CPU cores, minimum required is 2")
            return False
            
        # Check operating system
        os_name = platform.system()
        if os_name not in ["Windows", "Linux", "Darwin"]:
            logger.error(f"Unsupported operating system: {os_name}")
            return False
            
        logger.success(f"System requirements check passed: Python {python_version.major}.{python_version.minor}, {total_ram:.2f}GB RAM, {cpu_count} CPU cores, {os_name}")
        return True
    except Exception as e:
        logger.error(f"System requirements check failed: {e}")
        return False

def check_environment_variables():
    """
    Check if all required environment variables are set
    """
    env_categories = {
        "Azure": [
            "AZURE_SUBSCRIPTION_ID",
            "AZURE_TENANT_ID",
            "AZURE_RESOURCE_GROUP"
        ],
        "Database": [
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER"
        ],
        "API": [
            "API_PORT",
            "API_KEY"
        ],
        "Security": [
            "JWT_SECRET_KEY",
            "ENCRYPTION_KEY"
        ]
    }
    
    missing_vars = {}
    for category, vars in env_categories.items():
        missing = [var for var in vars if not os.environ.get(var)]
        if missing:
            missing_vars[category] = missing
            
    if missing_vars:
        for category, vars in missing_vars.items():
            logger.error(f"Missing required {category} environment variables: {', '.join(vars)}")
        return False
    
    # Additional check for Azure connection
    if "AZURE_SUBSCRIPTION_ID" in os.environ:
        subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
        logger.info(f"Azure subscription ID found: {subscription_id[:5]}...{subscription_id[-5:]}")
    
    logger.success("All required environment variables are set")
    return True

def parse_arguments():
    """Parse command line arguments for verification options"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scan and verify Zion system components")
    parser.add_argument("--skip-azure", action="store_true", help="Skip Azure resource checks")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker service checks")
    parser.add_argument("--skip-db", action="store_true", help="Skip database connectivity checks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    return parser.parse_args()

async def scan_and_verify():
    """Run all verification checks"""
    args = parse_arguments()
    
    # Configure logger based on verbosity
    log_level = "DEBUG" if args.verbose else "INFO"
    logger.remove()
    logger.add(sys.stderr, level=log_level)
    logger.add("logs/verification.log", rotation="10 MB", level="INFO")
    
    logger.info("Starting system scan and verification...")

    # System requirements are critical, check first
    if not check_system_requirements():
        logger.critical("System does not meet minimum requirements")
        return False

    # Check environment variables
    if not check_environment_variables():
        logger.warning("Missing required environment variables")
        # Continue with other checks, but note the warning

    # Check config files
    if not check_config_files():
        logger.error("Config file check failed")
        return False

    # Prepare checks based on arguments
    checks = [check_redis(), check_api(), check_disk_space(), check_gpu_availability()]
    check_names = ["Redis", "API", "Disk Space", "GPU"]
    
    if not args.skip_db:
        checks.append(check_database())
        check_names.append("Database")
    
    if not args.skip_docker:
        checks.append(check_docker())
        check_names.append("Docker")
    
    if not args.skip_azure:
        checks.append(check_azure_resources())
        check_names.append("Azure Resources")

    # Run all checks in parallel
    results = await asyncio.gather(*checks, return_exceptions=True)
    
    all_passed = True
    
    # Process results
    for name, result in zip(check_names, results):
        if isinstance(result, Exception):
            logger.error(f"{name} check threw an exception: {result}")
            all_passed = False
        elif not result:
            logger.error(f"{name} check failed")
            all_passed = False
        else:
            logger.success(f"{name} check passed")
    
    if all_passed:
        logger.info("All checks passed successfully")
        return True
    else:
        logger.error("One or more checks failed")
        return False

if __name__ == "__main__":
    sys.exit(0 if asyncio.run(scan_and_verify()) else 1)
