"""
Example demonstrating how to use standard logging in the application.
"""
import logging

# Define consistent log format
LOG_FORMAT = '%(levelname)s:     %(message)s'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
)

# Get a module-specific logger
logger = logging.getLogger(__name__)

def main():
    """Run the logging example."""
    # Log at different levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Log with context
    user_id = "user123"
    action = "login"
    logger.info(f"User {user_id} performed action: {action}")
    
    # Log exceptions
    try:
        result = 1 / 0
    except Exception as e:
        logger.exception(f"An error occurred: {e}")


if __name__ == "__main__":
    main() 