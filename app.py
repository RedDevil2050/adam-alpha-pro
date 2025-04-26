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
