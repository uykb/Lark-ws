import logging
import sys

def setup_logger():
    """
    Sets up a centralized logger for the application.
    """
    logger = logging.getLogger("CryptoSignalBot")
    if not logger.handlers: # Avoid adding handlers multiple times
        logger.setLevel(logging.INFO)
        
        # Create a handler to print to console
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Create a formatter and set it for the handler
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add the handler to the logger
        logger.addHandler(handler)
        
    return logger

# Instantiate the logger to be imported by other modules
log = setup_logger()
