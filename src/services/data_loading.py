"""Data loading utilities for participant federated learning."""

import json
import logging
import os
from pathlib import Path

import numpy as np


def load_tv_vocabulary(vocabulary_path):
    """Load the TV series vocabulary from the specified JSON file."""
    with open(vocabulary_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_participant_ratings(private_folder):
    """Load participant's ratings from the private folder."""
    ratings_path = os.path.join(private_folder, "ratings.npy")
    return np.load(ratings_path, allow_pickle=True).item()


def load_global_item_factors(save_path):
    """Load the global item factors matrix (V)."""
    global_V_path = os.path.join(save_path, "global_V.npy")
    return np.load(global_V_path)


def load_or_initialize_user_matrix(user_id, latent_dim, save_path):
    """Load existing user matrix or initialize a new one.

    Ensures the loaded vector matches the provided latent_dim. If a previously
    saved vector has a different size (e.g., latent_dim changed from 10 to 20),
    it will be resized to match the new dimension by:
      - Extending with small random values if smaller than latent_dim
      - Truncating if larger than latent_dim
    The adjusted vector is saved back to disk.
    """
    user_matrix_path = os.path.join(save_path, "U.npy")
    if os.path.exists(user_matrix_path):
        U_u = np.load(user_matrix_path)
        if U_u.shape != (latent_dim,):
            old_dim = U_u.shape[0]
            if old_dim < latent_dim:
                # Extend with small random values
                extension = np.random.normal(scale=0.01, size=(latent_dim - old_dim,))
                U_u = np.concatenate([U_u, extension])
                logging.info(
                    f"Resized user matrix for {user_id} from {old_dim} -> {latent_dim} (extended)."
                )
            else:
                # Truncate to new latent_dim
                U_u = U_u[:latent_dim]
                logging.info(
                    f"Resized user matrix for {user_id} from {old_dim} -> {latent_dim} (truncated)."
                )
            # Persist the resized vector
            os.makedirs(save_path, exist_ok=True)
            np.save(user_matrix_path, U_u)
        else:
            logging.info(f"Loaded existing user matrix for {user_id}.")
    else:
        U_u = initialize_user_matrix(user_id, latent_dim, save_path)
    return U_u


def initialize_user_matrix(user_id, latent_dim, save_path):
    """Initialize a new user matrix with random values."""
    os.makedirs(save_path, exist_ok=True)
    U_u = np.random.normal(scale=0.01, size=(latent_dim,))
    user_matrix_path = os.path.join(save_path, "U.npy")
    np.save(user_matrix_path, U_u)
    logging.info(f"Initialized and saved user matrix for {user_id}.")
    return U_u
