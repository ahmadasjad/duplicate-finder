"""Main application entry point."""

import logging


logger = logging.getLogger(__name__)

from app.ui import run_app

if __name__ == "__main__":
    run_app()
