"""Federated learning workflow service for participant."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import numpy as np

from src.config import APP_NAME
from src.core import (
    setup_environment,
    get_private_path,
    get_shared_folder_path,
    get_restricted_public_folder,
)
from src.federated_learning.sequence_data import SequenceData, create_view_counts_vector
from src.federated_learning.bpr_participant_finetuning import participant_fine_tuning


# Status tracking
fl_status = {
    "status": "idle",
    "message": "",
    "last_updated": None,
    "last_fine_tuning": None,
}


def get_fl_status():
    """Get current federated learning status."""
    return fl_status


def clear_user_models(private_folder):
    """
    Clear existing user models to prevent overfitting during retraining.
    
    This ensures fine-tuning starts fresh from the global model rather than
    building on top of an already-trained local model, which causes cumulative
    overfitting when retraining multiple times.
    
    Deletes:
    - svd_training/U.npy (user embedding matrix)
    - svd_training/updated_V.npy (locally updated item factors)
    
    Preserves:
    - global_V.npy (from aggregator - read only)
    - delta_V.npy (output for aggregator - will be regenerated)
    
    Args:
        private_folder: Path to the participant's private folder
    """
    svd_training_path = Path(private_folder) / "svd_training"
    
    files_to_delete = [
        svd_training_path / "U.npy",
        svd_training_path / "updated_V.npy",
    ]
    
    for file_path in files_to_delete:
        if file_path.exists():
            try:
                os.remove(file_path)
                logging.info(f"Cleared existing user model: {file_path}")
            except Exception as e:
                logging.warning(f"Could not delete {file_path}: {e}")


def load_csv_to_numpy(file_path: str) -> np.ndarray:
    """Load a CSV file into a NumPy array, skipping empty rows."""
    import csv
    cleaned_data = []
    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            # Skip empty rows or rows that don't have expected columns
            if row and len(row) >= 2 and row[0].strip():
                cleaned_data.append(row)
    return np.array(cleaned_data)


def check_viewing_history_exists(profile: str = "profile_0") -> dict:
    """
    Check if viewing history is available and return details.
    
    Only checks for user-uploaded viewing history in the private folder.
    
    Returns:
        dict: { exists: bool, source: str|None, path: str|None }
    """
    private_path = get_private_path(profile)
    user_csv = private_path / "NetflixViewingHistory.csv"
    
    if user_csv.exists():
        return {"exists": True, "source": "user_upload", "path": str(user_csv)}

    return {"exists": False, "source": None, "path": None}


def get_viewing_history(profile: str = "profile_0"):
    """
    Get viewing history from user-uploaded file.
    
    Only loads from the user's private folder where uploaded viewing history is stored.
    
    Returns:
        tuple: (file_path, viewing_history_array) or (None, None) if not found
    """
    private_path = get_private_path(profile)
    user_csv = private_path / "NetflixViewingHistory.csv"
    
    if user_csv.exists():
        logging.info(f"Loading viewing history from user upload: {user_csv}")
        return str(user_csv), load_csv_to_numpy(str(user_csv))

    logging.warning("No viewing history found. User must upload their Netflix viewing history.")
    return None, None


def prepare_participant_data(
    restricted_shared_folder,
    private_folder,
    viewing_history,
    click_history=None,
):
    """
    Prepare participant data for federated learning.
    
    Creates:
    - Sequence data from viewing history
    - View counts vector
    - Ratings dictionary
    - Aggregated activity for recommendations
    
    Args:
        restricted_shared_folder: Path to aggregator's shared folder
        private_folder: Path to participant's private folder
        viewing_history: NumPy array of viewing history [Title, Date]
        click_history: Optional list of clicked items to augment viewing history
    """
    logging.info("Preparing participant data for federated learning...")
    
    # Augment viewing history with click history (clicked items = implicit watches)
    if click_history and len(click_history) > 0:
        logging.info(f"Augmenting viewing history with {len(click_history)} clicked items...")
        click_entries = []        
        for click in click_history:
            name = click.get('name', '')
            if name:
                # Add as a viewing entry: [Title, Date]
                click_entry = [name, datetime.now().strftime('%d/%m/%Y')]
                click_entries.append(click_entry)
        
        if click_entries:
            click_array = np.array(click_entries)
            viewing_history = np.vstack([viewing_history, click_array])
            logging.info(f"Added {len(click_entries)} click entries to viewing history.")

        logging.info(f"click entries: {click_entries}")
        logging.info(f"viewing history: {viewing_history}")

    # Create sequence data
    sequence_recommender = SequenceData(viewing_history)
    logging.debug("Sequence data created from viewing history.")

    # Create view counts vector
    view_counts_vector = create_view_counts_vector(
        restricted_shared_folder, sequence_recommender.aggregated_data
    )
    
    # Save view counts vector
    private_tvseries_views_file = private_folder / "tvseries_views_sparse_vector.npy"
    np.save(str(private_tvseries_views_file), view_counts_vector)
    logging.debug(f"View counts vector saved to {private_tvseries_views_file}.")

    # Create ratings dictionary from sequence data
    # (convert view counts to implicit ratings - watched = positive signal)
    ratings = {}
    for _, row in sequence_recommender.aggregated_data.iterrows():
        show_name = row["show"]
        # Implicit rating based on view count (normalized)
        total_views = row["Total_Views"]
        implicit_rating = min(5.0, 1.0 + np.log1p(total_views))  # Log scale, capped at 5
        ratings[show_name] = implicit_rating
    
    # Save ratings
    ratings_path = private_folder / "ratings.npy"
    np.save(str(ratings_path), ratings)
    logging.debug(f"Ratings saved to {ratings_path}.")

    # Create aggregated activity for recommendations
    # Format: (title, week, n_watched, rating)
    aggregated_data = sequence_recommender.aggregated_data
    activity_list = []
    for _, row in aggregated_data.iterrows():
        week = row["First_Seen"].isocalendar()[1] if hasattr(row["First_Seen"], "isocalendar") else 1
        activity_list.append([
            row["show"],
            week,
            row["Total_Views"],
            ratings.get(row["show"], 3.0)
        ])
    
    activity_array = np.array(activity_list, dtype=object)
    activity_path = private_folder / "netflix_aggregated.npy"
    np.save(str(activity_path), activity_array)
    logging.debug(f"Aggregated activity saved to {activity_path}.")

    return sequence_recommender, view_counts_vector, ratings


def run_fine_tuning(profile: str = "profile_0", epsilon: float = 1.0):
    """
    Run the participant fine-tuning process.
    
    This trains the local BPR model and produces delta_V for aggregation.
    """
    global fl_status
    
    try:
        fl_status = {
            "status": "fine_tuning",
            "message": "Running participant fine-tuning...",
            "last_updated": datetime.now().isoformat(),
            "last_fine_tuning": fl_status.get("last_fine_tuning"),
        }
        
        # Setup environment
        restricted_shared_folder, restricted_public_folder, private_folder = setup_environment(profile)
        
        logging.info(f"Environment setup complete for {profile}")
        logging.info(f"  Shared folder: {restricted_shared_folder}")
        logging.info(f"  Public folder: {restricted_public_folder}")
        logging.info(f"  Private folder: {private_folder}")
        
        # Check if global model exists
        global_v_path = restricted_shared_folder / "global_V.npy"
        if not global_v_path.exists():
            fl_status = {
                "status": "error",
                "message": f"Global model not found at {global_v_path}. Aggregator may not be running.",
                "last_updated": datetime.now().isoformat(),
                "last_fine_tuning": fl_status.get("last_fine_tuning"),
            }
            logging.error(f"Global model not found: {global_v_path}")
            return False
        
        # Check if we have ratings data
        ratings_path = private_folder / "ratings.npy"
        if not ratings_path.exists():
            # Try to prepare data from viewing history
            logging.info("Ratings not found, attempting to prepare from viewing history...")
            file_path, viewing_history = get_viewing_history(profile)
            
            if viewing_history is None:
                fl_status = {
                    "status": "no_viewing_history",
                    "message": "No viewing history found. Please upload your Netflix viewing history.",
                    "last_updated": datetime.now().isoformat(),
                    "last_fine_tuning": fl_status.get("last_fine_tuning"),
                }
                logging.error("Fine-tuning failed: No viewing history available")
                return False
            
            prepare_participant_data(
                restricted_shared_folder,
                private_folder,
                viewing_history,
            )
        
        # Run fine-tuning
        logging.info(f"Starting BPR fine-tuning for {profile}...")
        participant_fine_tuning(
            user_id=profile,
            private_path=private_folder,
            global_path=restricted_shared_folder,
            restricted_path=restricted_public_folder,
            epsilon=epsilon,
            noise_type="gaussian",
            clipping_threshold=None,
            plot=False,
            dp_all=False,
        )
        
        fl_status = {
            "status": "ready",
            "message": "Fine-tuning completed successfully",
            "last_updated": datetime.now().isoformat(),
            "last_fine_tuning": datetime.now().isoformat(),
        }
        
        logging.info("Fine-tuning completed successfully!")
        return True
        
    except Exception as e:
        logging.error(f"Error during fine-tuning: {e}")
        fl_status = {
            "status": "error",
            "message": str(e),
            "last_updated": datetime.now().isoformat(),
            "last_fine_tuning": fl_status.get("last_fine_tuning"),
        }
        return False


def run_full_fl_workflow(profile: str = "profile_0", epsilon: float = 1.0, click_history: list = None):
    """
    Run the complete federated learning workflow:
    1. Setup environment
    2. Load/prepare viewing history data (augmented with click history)
    3. Run fine-tuning
    4. Trigger recommendation computation
    
    Args:
        profile: User profile identifier
        epsilon: Privacy budget for differential privacy
        click_history: Optional list of clicked items to augment training data
    
    Returns:
        bool: True if successful, False otherwise
    """
    global fl_status
    
    try:
        click_count = len(click_history) if click_history else 0
        fl_status = {
            "status": "running",
            "message": f"Starting federated learning workflow with {click_count} click history items...",
            "last_updated": datetime.now().isoformat(),
            "last_fine_tuning": fl_status.get("last_fine_tuning"),
        }
        
        # Step 1: Setup environment
        restricted_shared_folder, restricted_public_folder, private_folder = setup_environment(profile)
        
        # Step 2: Get viewing history
        file_path, viewing_history = get_viewing_history(profile)
        
        if viewing_history is None:
            fl_status = {
                "status": "no_viewing_history",
                "message": "No viewing history found. Please upload your Netflix viewing history.",
                "last_updated": datetime.now().isoformat(),
                "last_fine_tuning": fl_status.get("last_fine_tuning"),
            }
            logging.error("FL workflow failed: No viewing history found")
            return False
        
        # Step 2.5: Clear existing user models to prevent overfitting
        # This ensures we start fresh from the global model each time
        clear_user_models(private_folder)
        
        # Step 3: Prepare participant data (with click history augmentation)
        prepare_participant_data(
            restricted_shared_folder,
            private_folder,
            viewing_history,
            click_history=click_history,
        )
        
        # Step 4: Run fine-tuning
        success = run_fine_tuning(profile, epsilon)
        
        if success:
            # Step 5: Trigger recommendations
            from src.services.recommendations import run_recommendation_computation
            run_recommendation_computation()
        
        return success
        
    except Exception as e:
        logging.error(f"Error in FL workflow: {e}")
        fl_status = {
            "status": "error",
            "message": str(e),
            "last_updated": datetime.now().isoformat(),
            "last_fine_tuning": fl_status.get("last_fine_tuning"),
        }
        return False


def check_fine_tuning_needed(profile: str = "profile_0"):
    """
    Check if fine-tuning is needed based on:
    - Whether delta_V exists
    - Whether global model has been updated since last fine-tuning
    
    Returns:
        bool: True if fine-tuning should be run
    """
    restricted_shared_folder, restricted_public_folder, private_folder = setup_environment(profile)
    
    # Check if delta_V exists
    delta_v_path = restricted_public_folder / "svd_training" / "delta_V.npy"
    if not delta_v_path.exists():
        logging.info("delta_V.npy not found - fine-tuning needed")
        return True
    
    # Check if U.npy exists (user matrix)
    u_path = private_folder / "svd_training" / "U.npy"
    if not u_path.exists():
        logging.info("U.npy not found - fine-tuning needed")
        return True
    
    # Check timestamps - if global_V is newer than our delta_V, we should re-train
    global_v_path = restricted_shared_folder / "global_V.npy"
    if global_v_path.exists() and delta_v_path.exists():
        global_mtime = global_v_path.stat().st_mtime
        delta_mtime = delta_v_path.stat().st_mtime
        if global_mtime > delta_mtime:
            logging.info("global_V.npy is newer than delta_V.npy - fine-tuning needed")
            return True
    
    return False
