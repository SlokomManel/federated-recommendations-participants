"""File I/O operations for recommendations."""

import json
from src.core import get_private_path


def recommendations_exist():
    """Check if recommendation files exist."""
    participant_private_path = get_private_path()
    raw_results = participant_private_path / "raw_recommendations.json"
    reranked_results = participant_private_path / "reranked_recommendations.json"
    return raw_results.exists() and reranked_results.exists()


def load_recommendations():
    """Load recommendation data from JSON files."""
    participant_private_path = get_private_path()
    raw_results = participant_private_path / "raw_recommendations.json"
    reranked_results = participant_private_path / "reranked_recommendations.json"

    with open(raw_results, "r", encoding="utf-8") as f:
        all_raw_recommends = json.load(f)

    with open(reranked_results, "r", encoding="utf-8") as f:
        all_reranked_recommends = json.load(f)

    # Return all saved recommendations sorted by score
    raw_recommends = sorted(all_raw_recommends, key=lambda x: x["raw_score"], reverse=True)
    reranked_recommends = sorted(all_reranked_recommends, key=lambda x: x["raw_score"], reverse=True)

    return raw_recommends, reranked_recommends
