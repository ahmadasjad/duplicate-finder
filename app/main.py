"""Main application entry point."""

import logging
import os
import sys
from app.config import LOG_LEVEL
from app.ui import run_app

def setup_logging():
    """Configure logging based on environment."""
    log_level = LOG_LEVEL
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Console logging
    logging.basicConfig(
        level=LOG_LEVEL,
        format=log_format
    )

    # File logging in production
    if os.getenv("ENVIRONMENT") == "production":
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)

    return logging.getLogger(__name__)

def main():
    """Main application entry point."""
    logger = setup_logging()

    try:
        logger.info("Starting Duplicate File Finder")
        run_app()
    except Exception as e:
        logger.error("Application failed: %s", str(e), exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Application shutdown")

if __name__ == "__main__":
    main()
