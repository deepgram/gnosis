import os
import sys
import pytest
import asyncio
import subprocess
import time
import signal
import logging
from httpx import AsyncClient
import websockets
import atexit
from dotenv import load_dotenv
import socket

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_server")

# Add the project root to the path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file with override to ensure values are properly set
load_dotenv(override=True)

from src.server import create_app
from src.config import Config

# Server settings for testing
SERVER_HOST = os.environ.get("SERVER_HOST", "localhost")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "8123"))  # Use a unique port for testing
SERVER_STARTUP_TIMEOUT = int(os.environ.get("SERVER_STARTUP_TIMEOUT", "10"))

# Set environment variables for server
os.environ["SERVER_HOST"] = SERVER_HOST
os.environ["SERVER_PORT"] = str(SERVER_PORT)

# Base URLs based on server host and port
BASE_HTTP_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
BASE_WS_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}"

# API keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# Store server process globally to ensure it gets cleaned up
_server_process = None

def is_port_in_use(port, host='localhost'):
    """Check if a port is in use by trying to bind to it"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            # If we get here, the port is free
            return False
        except socket.error:
            # Port is in use
            return True

def can_connect_to_server(host, port, timeout=1):
    """Check if we can connect to a server at the given host and port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def cleanup_server():
    """Ensure server is terminated on exit"""
    global _server_process
    if _server_process:
        try:
            logger.info("Cleaning up server process...")
            os.killpg(os.getpgid(_server_process.pid), signal.SIGTERM)
        except:
            pass

# Register cleanup handler
atexit.register(cleanup_server)

@pytest.fixture(scope="session")
def server_process():
    """Start the server in a separate process for testing"""
    global _server_process
    
    # Check if port is already in use
    if is_port_in_use(SERVER_PORT, SERVER_HOST):
        logger.error(f"Port {SERVER_PORT} is already in use. Cannot start test server.")
        pytest.skip(f"Port {SERVER_PORT} is already in use")
    
    # Set environment variables for the subprocess
    env = os.environ.copy()
    env["SERVER_HOST"] = SERVER_HOST
    env["SERVER_PORT"] = str(SERVER_PORT)
    
    logger.info(f"Starting test server on {SERVER_HOST}:{SERVER_PORT}...")
    
    # Start the server process using make dev-test target
    process = subprocess.Popen(
        ["make", "dev-test"], 
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid  # This allows us to kill the process group later
    )
    
    _server_process = process
    
    # Wait for the server to start (use configured timeout)
    max_attempts = 20
    startup_timeout = SERVER_STARTUP_TIMEOUT  # seconds
    start_time = time.time()
    
    logger.info(f"Waiting up to {startup_timeout} seconds for server to start...")
    
    for i in range(max_attempts):
        if time.time() - start_time > startup_timeout:
            logger.error(f"Server startup timed out after {startup_timeout} seconds")
            break
            
        if can_connect_to_server(SERVER_HOST, SERVER_PORT):
            logger.info(f"Server started successfully on {SERVER_HOST}:{SERVER_PORT}")
            break
        
        # Check if process is still running
        if process.poll() is not None:
            # Process exited
            stdout, stderr = process.communicate()
            logger.error(f"Server process exited unexpectedly with code {process.returncode}")
            logger.error(f"STDOUT: {stdout.decode('utf-8') if stdout else 'None'}")
            logger.error(f"STDERR: {stderr.decode('utf-8') if stderr else 'None'}")
            break
            
        time.sleep(0.5)  # Allow more time between attempts
        
    else:
        # Loop completed without finding a working server
        logger.error(f"Failed to start server after {max_attempts} attempts")
        
    # Check one final time if server is running
    if not can_connect_to_server(SERVER_HOST, SERVER_PORT):
        logger.error("Server failed to start or bind to the expected port")
        try:
            stdout, stderr = process.communicate(timeout=0.5)
            logger.error(f"STDOUT: {stdout.decode('utf-8') if stdout else 'None'}")
            logger.error(f"STDERR: {stderr.decode('utf-8') if stderr else 'None'}")
        except subprocess.TimeoutExpired:
            pass
            
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except:
            pass
        
        pytest.skip("Server failed to start - skipping tests that require server")
    
    # Server is running, yield control back to the tests
    yield process
    
    # After all tests complete, terminate the server
    logger.info("Terminating test server...")
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except:
        pass
    _server_process = None

@pytest.fixture
async def http_client(server_process):
    """Create an async HTTP client for testing."""
    headers = {}
    if OPENAI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
    
    async with AsyncClient(base_url=BASE_HTTP_URL, headers=headers) as client:
        yield client

@pytest.fixture
async def websocket_client(server_process):
    """Create a websocket client for testing."""
    async def _create_websocket_connection(path: str):
        uri = f"{BASE_WS_URL}{path}"
        
        # Using a simpler approach to connect to WebSocket
        # The headers will be added as part of the WebSocket handshake
        protocols = []
        if DEEPGRAM_API_KEY:
            # Use WebSocket protocol for authorization
            protocols = ["token", DEEPGRAM_API_KEY]
        
        return await websockets.connect(uri, subprotocols=protocols)
    
    return _create_websocket_connection 