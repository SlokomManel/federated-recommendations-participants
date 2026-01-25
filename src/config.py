"""Configuration and environment setup."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

APP_NAME = os.getenv("APP_NAME", "federated-recommendations")
AGGREGATOR_DATASITE = os.getenv("AGGREGATOR_DATASITE")

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
UI_DIR = Path(__file__).parent.parent / "ui"


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
