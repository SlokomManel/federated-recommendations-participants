"""Recommendation computation service."""

import os
import json
import math
import logging
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

from src.core import get_private_path, get_shared_folder_path
from src.config import DATA_DIR


def get_recommendations_data(recommendation_list, df):
    """Convert recommendation list to enriched data with metadata from DataFrame.
    
    Uses augmented_titles.csv as data source with columns:
    - title: Title name
    - rating: Content rating (TV-MA, PG, etc.)
    - tmdb_score: TMDB rating value (used instead of IMDB)
    - cover_url: Poster image URL
    """
    recommendations_data = []
    for i, (name, idx, score) in enumerate(recommendation_list):
        print(f"\t{i+1} => {name}: {score:.4f}")

        try:
            row = df[df["title"].str.strip() == name].iloc[0]
        except IndexError:
            logging.warning(f"Could not find metadata for: {name}")
            continue
            
        safe_score = float(score) if not math.isnan(score) else 0.0

        # Get cover image from augmented_titles.csv
        img = row["cover_url"] if pd.notna(row.get("cover_url")) else ""
        
        # Language not available
        language = "N/A"
        
        # rating column contains content rating (TV-MA, PG, etc.)
        rating = row["rating"] if pd.notna(row.get("rating")) else "N/A"
        rating = str(rating) if rating not in (None, "") else "N/A"
        
        # Use tmdb_score instead of imdb_score
        tmdb_score = row["tmdb_score"] if pd.notna(row.get("tmdb_score")) else "N/A"
        
        entry = {
            "id": int(idx),
            "name": name,
            "language": language,
            "rating": rating,
            "imdb": tmdb_score,  # Keep "imdb" key for UI compatibility, but use TMDB score
            "tmdb_score": tmdb_score,
            "img": img,
            "count": int(safe_score),
            "raw_score": safe_score
        }
        recommendations_data.append(entry)
    return recommendations_data


def local_recommendation(local_path, global_path, tv_vocab, exclude_watched=True, additional_watched=None):
    """Main entry point for local recommendation generation."""
    from src.federated_learning.bpr_participant_local_recommendation import compute_recommendations

    global_V_path = os.path.join(global_path, "global_V.npy")
    user_U_path = os.path.join(local_path, "svd_training", "U.npy")
    user_aggregated_activity_path = os.path.join(local_path, "netflix_aggregated.npy")
    
    # Check for global model file
    if not os.path.exists(global_V_path):
        logging.error(f"Global model not found: {global_V_path}")
        raise FileNotFoundError(f"global_V.npy not found at {global_V_path}")
    
    if not os.path.exists(user_U_path) or not os.path.exists(user_aggregated_activity_path):
        logging.error(f"User data not found: U.npy ({user_U_path}) / netflix_aggregated.npy ({user_aggregated_activity_path})")
        return None, None

    user_U = np.load(user_U_path)
    global_V = np.load(global_V_path)
    user_aggregated_activity = np.load(user_aggregated_activity_path, allow_pickle=True).copy()
    
    # Treat click-history items as "watched" by adding them to the activity list.
    # `compute_recommendations()` expects an iterable of rows: (title, week, n_watched, rating).
    if additional_watched:
        new_rows = []
        for item_name in additional_watched:
            if not item_name:
                continue
            new_rows.append([item_name, 0, 1, 3.0])
        if new_rows:
            extra = np.array(new_rows, dtype=object)
            user_aggregated_activity = (
                np.vstack([user_aggregated_activity, extra])
                if user_aggregated_activity.size
                else extra
            )
            logging.debug(f"Added {len(new_rows)} click history items to aggregated activity.")

    raw_recommendations, reranked_recommendations = compute_recommendations(
        user_U, global_V, tv_vocab, user_aggregated_activity, exclude_watched=exclude_watched
    )

    # Use augmented_titles.csv as the single source of data with semicolon separator
    csv_file_path = DATA_DIR / "augmented_titles.csv"
    try:
        df = pd.read_csv(csv_file_path, sep=';')
    except Exception as e:
        print(f"> Error: Unable to read CSV from {csv_file_path}. Error: {e}")
        return None, None

    print("(Unprocessed) Recommended based on most recently watched:")
    raw_data = get_recommendations_data(raw_recommendations, df)
    print("(Re-ranked) Recommended based on most recently watched:")
    reranked_data = get_recommendations_data(reranked_recommendations, df) 

    return raw_data, reranked_data


# Global computation status
computation_status = {"status": "idle", "message": "", "last_updated": None}
_pending_click_history = []


def run_recommendation_computation():
    """Run the recommendation computation in the background."""
    global computation_status, _pending_click_history
    
    def _sanitize_for_strict_json(obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: _sanitize_for_strict_json(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize_for_strict_json(v) for v in obj]
        return obj

    try:
        computation_status = {
            "status": "computing",
            "message": "Running recommendation computation...",
            "last_updated": datetime.now().isoformat()
        }
        
        participant_private_path = get_private_path()
        shared_folder_path = get_shared_folder_path()
        
        # Load TV vocabulary
        tv_vocab = {}
        try:
            json_file_path = shared_folder_path / "vocabulary.json"
            with open(json_file_path, 'r', encoding='utf-8') as f:
                tv_vocab = json.load(f)
        except FileNotFoundError:
            # Check if the shared folder exists at all
            if not shared_folder_path.exists():
                error_msg = "Could not find aggregator shared folder. Please ensure SyftBox is running."
                error_status = "syftbox_not_running"
            else:
                error_msg = "Vocabulary file not found. The aggregator hasn't initialized the model files yet. Please wait and try again."
                error_status = "aggregator_not_initialized"
            logging.error(f"{error_msg} (path: {json_file_path})")
            computation_status = {
                "status": "error",
                "error_type": error_status,
                "message": error_msg,
                "last_updated": datetime.now().isoformat()
            }
            return
        except Exception as e:
            logging.error(f"Could not load TV vocabulary file: {e}")
            computation_status = {
                "status": "error",
                "error_type": "vocabulary_error",
                "message": f"Could not load TV vocabulary file: {e}",
                "last_updated": datetime.now().isoformat()
            }
            return
        
        additional_watched = []
        if _pending_click_history:
            additional_watched = [item.get('name') for item in _pending_click_history if item.get('name')]
            logging.info(f"Using {len(additional_watched)} click history items to enhance recommendations")
        
        raw_recommendations, reranked_recommendations = local_recommendation(
            participant_private_path,
            shared_folder_path,
            tv_vocab,
            exclude_watched=True,
            additional_watched=additional_watched,
        )
        
        _pending_click_history.clear()
        
        if raw_recommendations is None:
            computation_status = {
                "status": "error",
                "message": "Failed to compute recommendations",
                "last_updated": datetime.now().isoformat()
            }
            return
        
        # Save results
        raw_results_path = participant_private_path / "raw_recommendations.json"
        reranked_results_path = participant_private_path / "reranked_recommendations.json"
        
        os.makedirs(os.path.dirname(raw_results_path), exist_ok=True)

        raw_recommendations = _sanitize_for_strict_json(raw_recommendations)
        reranked_recommendations = _sanitize_for_strict_json(reranked_recommendations)

        with open(raw_results_path, 'w', encoding="utf-8") as f:
            json.dump(raw_recommendations, f, indent=4, allow_nan=False)
        
        with open(reranked_results_path, 'w', encoding="utf-8") as f:
            json.dump(reranked_recommendations, f, indent=4, allow_nan=False)
        
        computation_status = {
            "status": "ready",
            "message": "Recommendations computed successfully",
            "last_updated": datetime.now().isoformat()
        }
        
    except FileNotFoundError as e:
        error_str = str(e)
        logging.error(f"File not found during recommendation computation: {error_str}")
        
        # Determine user-friendly message based on which file is missing
        if "vocabulary.json" in error_str:
            error_msg = "Vocabulary file not found. The aggregator hasn't initialized the model files yet. Please wait and try again."
            error_type = "aggregator_not_initialized"
        elif "global_V" in error_str:
            error_msg = "Global model not found. The aggregator hasn't processed any data yet. Please wait for the aggregator to run."
            error_type = "aggregator_not_ready"
        else:
            error_msg = "Required model files not found. Please ensure SyftBox is running and the aggregator has been set up."
            error_type = "syftbox_not_running"
        
        computation_status = {
            "status": "error",
            "error_type": error_type,
            "message": error_msg,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        error_str = str(e)
        logging.error(f"Error during recommendation computation: {error_str}")
        computation_status = {
            "status": "error",
            "error_type": "error",
            "message": error_str,
            "last_updated": datetime.now().isoformat()
        }


def get_computation_status():
    """Get current computation status."""
    return computation_status


def set_pending_click_history(history):
    """Set pending click history for recommendation enhancement."""
    global _pending_click_history
    _pending_click_history = history
