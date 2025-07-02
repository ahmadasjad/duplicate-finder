"""Main application entry point."""

import logging

from app.ui import run_app


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    run_app()
