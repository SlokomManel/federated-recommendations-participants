"""Core SyftBox client and path utilities."""

import os
from functools import lru_cache
from pathlib import Path

from syft_core import Client as SyftboxClient
from syft_core.permissions import SyftPermission

from src.config import APP_NAME, AGGREGATOR_DATASITE
from src.preflight import PreflightError, require_preflight


@lru_cache(maxsize=1)
def get_client() -> SyftboxClient:
    """
    Lazily initialize the SyftBox client.

    This avoids crashing at import time, and ensures we can provide friendly,
    actionable diagnostics when SyftBox isn't configured correctly.
    """
    require_preflight()

    from syft_core import SyftClientConfig  # local import for cleaner failures

    config = SyftClientConfig.load()
    return SyftboxClient(config)


def get_private_path(profile: str = "profile_0"):
    """Get the participant's private data path."""
    client = get_client()
    return Path(client.config.data_dir) / "private" / APP_NAME / profile


def get_shared_folder_path():
    """Get the shared folder path from the aggregator."""
    if not AGGREGATOR_DATASITE:
        raise PreflightError(
            "Missing `AGGREGATOR_DATASITE`.\n\n"
            "Fix:\n"
            "- Set `AGGREGATOR_DATASITE` in `.env` to the aggregator's datasite email.\n"
        )
    client = get_client()
    datasites_path = Path(client.datasite_path.parent)
    return datasites_path / AGGREGATOR_DATASITE / "app_data" / APP_NAME / "shared"


def get_restricted_public_folder(profile: str = "profile_0"):
    """Get the restricted public folder path (aggregator can read delta_V from here)."""
    client = get_client()
    return client.app_data(APP_NAME) / profile


def setup_environment(profile: str = "profile_0"):
    """
    Set up the participant environment with proper folder structure and permissions.
    
    Creates:
    - Private folder: for user data (ratings, U matrix, viewing history)
    - Restricted public folder: for data shared with aggregator (delta_V)
    
    Returns:
        tuple: (restricted_shared_folder, restricted_public_folder, private_folder)
    """
    if not AGGREGATOR_DATASITE:
        raise PreflightError(
            "Missing `AGGREGATOR_DATASITE`.\n\n"
            "Fix:\n"
            "- Set `AGGREGATOR_DATASITE` in `.env` to the aggregator's datasite email.\n"
        )

    client = get_client()

    # Private folder (outside datasite path for security)
    private_folder = get_private_path(profile)
    private_folder.mkdir(parents=True, exist_ok=True)
    
    # Restricted public folder (in app_data, aggregator can read)
    restricted_public_folder = get_restricted_public_folder(profile)
    os.makedirs(restricted_public_folder, exist_ok=True)
    
    # Set permissions for restricted public folder - aggregator can read
    permissions = SyftPermission.datasite_default(context=client, dir=restricted_public_folder)
    permissions.add_rule(
        path="**",
        user=AGGREGATOR_DATASITE,
        permission="read",
    )
    permissions.save(restricted_public_folder)
    
    # Shared folder from aggregator (read-only for us)
    restricted_shared_folder = get_shared_folder_path()
    
    return restricted_shared_folder, restricted_public_folder, private_folder


def get_datasites_path():
    """Get the datasites path."""
    client = get_client()
    return Path(client.datasite_path.parent)
