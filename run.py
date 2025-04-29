import sys
import subprocess
import time
import os
import tempfile
import ssl
import shutil
import socket
import pkg_resources
from importlib.metadata import version, PackageNotFoundError, distributions
from packaging.version import parse as parse_version

def check_network():
    dns_servers = [
        ("8.8.8.8", 53),  # Google DNS
        ("1.1.1.1", 53),  # Cloudflare DNS
        ("208.67.222.222", 53)  # OpenDNS
    ]
    for dns in dns_servers:
        try:
            socket.create_connection(dns, timeout=1)
            return True
        except (OSError, socket.timeout):
            continue
    return False

def verify_installation(package_name):
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None

def check_dependencies():
    # First check network connectivity
    online = check_network()
    if not online:
        print("Warning: No network connection detected. Verifying cached packages...")
        # Verify critical packages are available offline
        critical_packages = ['fastapi', 'uvicorn', 'loguru', 'redis', 'sqlalchemy', 'psutil']
        missing_critical = [pkg for pkg in critical_packages if not verify_installation(pkg)]
        if missing_critical:
            print(f"Error: Critical packages missing: {missing_critical}")
            print("Network connection required for first installation")
            sys.exit(1)

    def get_pip_command():
        # Check proxy settings
        proxy = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
        cmd = [sys.executable, "-m", "ensurepip"]
        if proxy:
            cmd.extend(['--proxy', proxy])
        return cmd

    def download_get_pip():
        import urllib.request
        temp_dir = tempfile.gettempdir()
        get_pip_path = os.path.join(temp_dir, "get-pip.py")
        
        # Try to use cached version if offline
        if os.path.exists(get_pip_path) and not check_network():
            if os.access(get_pip_path, os.R_OK):
                print("Using cached get-pip.py")
                return get_pip_path
            
        # Clean up existing file if present
        if os.path.exists(get_pip_path):
            try:
                os.remove(get_pip_path)
            except OSError:
                get_pip_path = os.path.join(temp_dir, f"get-pip-{time.time()}.py")

        urls = [
            "https://bootstrap.pypa.io/get-pip.py",
            "https://raw.githubusercontent.com/pypa/get-pip/master/public/get-pip.py"
        ]

        for url in urls:
            try:
                # Try with and without SSL verification
                try:
                    urllib.request.urlretrieve(url, get_pip_path)
                except ssl.SSLError:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    with urllib.request.urlopen(url, context=ctx) as response, open(get_pip_path, 'wb') as f:
                        shutil.copyfileobj(response, f)
                
                # Verify file was downloaded and is readable
                if os.path.exists(get_pip_path) and os.access(get_pip_path, os.R_OK):
                    return get_pip_path
            except Exception as e:
                print(f"Failed to download from {url}: {e}")
                continue
        
        return None

    try:
        import pip
        if parse_version(pip.__version__) < parse_version('21.0'):
            raise ImportError("Pip version too old")
    except ImportError:
        print("pip is not installed or outdated. Installing/upgrading pip...")

        # Try multiple installation methods
        for method in [
            lambda: subprocess.check_call(get_pip_command(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60),
            lambda: subprocess.check_call([sys.executable, download_get_pip()], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60),
            lambda: subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        ]:
            try:
                method()
                break
            except Exception as e:
                print(f"Installation attempt failed: {e}")
                continue
        else:
            print("All pip installation methods failed")
            sys.exit(1)

    # First upgrade pip itself with retry
    for attempt in range(3):
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60
            )
            break
        except Exception:
            if attempt == 2:
                print("Warning: Failed to upgrade pip after 3 attempts")
            time.sleep(1)

    pkg_mapping = {
        'prometheus-client': 'prometheus_client',
        'prometheus_client': 'prometheus_client',
        'uvicorn': 'uvicorn[standard]',
        'fastapi': 'fastapi[all]',
        'aiohttp': 'aiohttp[speedups]',
        'httpx': 'httpx[http2]',
        'websockets': 'websockets',
        'python-multipart': 'python_multipart',
        'slowapi': 'slowapi[all]',
        'redis': 'redis[hiredis]',
        'sqlalchemy': 'sqlalchemy[asyncio]'
    }
    
    required = {
        'prometheus-client': '0.9.0',
        'psutil': '5.8.0',
        'numpy': '1.20.0',
        'fastapi': '0.68.0',
        'uvicorn': '0.15.0',
        'loguru': '0.5.3',
        'python-multipart': '0.0.5',
        'pydantic': '1.8.2',
        'typing-extensions': '4.0.0',
        'aiohttp': '3.8.0',
        'httpx': '0.23.0',
        'websockets': '10.0',
        'slowapi': '0.1.8',
        'redis': '4.5.0',
        'sqlalchemy': '1.4.41',
        'hiredis': '2.0.0',
        'limits': '3.5.0'
    }
    
    try:
        installed = {}
        installed_packages = {dist.metadata['Name']: dist.metadata['Version'] for dist in distributions() if hasattr(dist.metadata, 'Name') and hasattr(dist.metadata, 'Version')}
        for pkg, ver in installed_packages.items():
            try:
                # Normalize package names and handle multiple formats
                name = pkg.replace('-', '_').lower()
                installed[name] = ver
                if name in pkg_mapping:
                    installed[pkg_mapping[name]] = ver
            except Exception as e:
                print(f"Warning: Error processing package {pkg}: {e}")
                continue
        
        print("Detected installed packages:", installed.keys())
    
        missing = []
        outdated = []
        
        for package, min_version in required.items():
            # Use mapped name if exists
            check_name = pkg_mapping.get(package, package.replace('-', '_').lower())
            try:
                if check_name not in installed:
                    missing.append(package)
                elif parse_version(installed[check_name]) < parse_version(min_version):
                    outdated.append(package)
            except (TypeError, ValueError) as e:
                print(f"Warning: Version comparison failed for {package}: {e}")
                missing.append(package)

        if missing or outdated:
            print("Installing/updating dependencies...")
            try:
                packages_to_install = missing + outdated
                process = subprocess.Popen(
                    [
                        sys.executable, 
                        "-m", 
                        "pip", 
                        "install", 
                        *[f"{pkg}>={required[pkg]}" for pkg in packages_to_install]
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                # Wait for installation with timeout
                try:
                    stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
                    if process.returncode != 0:
                        print(f"Installation failed for some packages:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")
                    else:
                        print("Dependencies installed successfully.")
                except subprocess.TimeoutExpired:
                    process.kill()
                    print("Dependency installation timed out after 5 minutes")
                    
            except Exception as e:
                print(f"Failed to install some dependencies: {str(e)}")

    except Exception as e:
        print(f"Failed to check/install dependencies, but continuing: {str(e)}")

# Check dependencies before importing
check_dependencies()

# Update import section after check_dependencies()
import asyncio
import uvicorn
from loguru import logger
import sys
from pathlib import Path

# Add project root and verify backend package
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import backend
    from backend.startup import initialize_system
    from backend.api.main import app
    from backend.utils.system_monitor import SystemMonitor
except ImportError as e:
    logger.error(f"Failed to import backend modules: {e}")
    logger.info(f"Python path: {sys.path}")
    logger.info("Ensure backend package structure is correct")
    sys.exit(1)

async def main():
    try:
        # Initialize system first
        orchestrator, monitor = await initialize_system()
        
        # The FastAPI app object is imported, but Uvicorn needs the string path
        app_module_path = "backend.api.main:app" 

        # Start uvicorn server
        config = uvicorn.Config(
            app=app_module_path, # Use the string path for Uvicorn
            host="0.0.0.0",
            port=8000,
            reload=False, # Set reload to False for Docker stability
            log_level="info"
        )
        server = uvicorn.Server(config)

        # Accessing app.state before server starts is unreliable.
        # If you need to pass orchestrator/monitor, consider dependency injection
        # or accessing state within request handlers after the app starts.
        # logger.info("Orchestrator and monitor initialized, starting server...")

        await server.serve()
        
    except Exception as e:
        logger.error(f"System launch failed: {e}")
        # Optionally: Add more specific error handling or cleanup
        raise

if __name__ == "__main__":
    asyncio.run(main())
