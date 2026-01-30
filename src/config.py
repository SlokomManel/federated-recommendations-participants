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

# Runtime item-factor normalization (scales item embeddings before scoring)
# Default: enabled to defensively bound dot-product magnitudes that can arise
# from large global item factors. Override via env var `NORMALIZE_ITEM_FACTORS=false`.
NORMALIZE_ITEM_FACTORS = os.getenv("NORMALIZE_ITEM_FACTORS", "true").lower() in ("1", "true", "yes")
# Method: 'l2' (row-wise L2 unit-norm) or 'scale_mean' (scale all rows by target mean norm)
# Default method: 'l2' (unit row norms) — preferred for stable ranking behavior.
ITEM_FACTOR_NORM_METHOD = os.getenv("ITEM_FACTOR_NORM_METHOD", "l2")
# Target mean norm used by 'scale_mean'
ITEM_FACTOR_NORM_TARGET = float(os.getenv("ITEM_FACTOR_NORM_TARGET", "1.0"))

# Display normalization for UI percentages: None | 'sigmoid' | 'minmax'
# When 'minmax', scores for the displayed recommendations are min-max scaled per-user
DISPLAY_SCORE_METHOD = os.getenv("DISPLAY_SCORE_METHOD", "minmax")

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
UI_DIR = Path(__file__).parent.parent / "ui"

# Use augmented_titles.csv as the single source of data with semicolon separator
TITLES_DB_PATH = DATA_DIR / "augmented_titles.csv"
TITLES_DB_SEPARATOR = ";"


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
