"""Data enrichment services for recommendations."""

import csv
import math
import logging
from pathlib import Path

from src.config import DATA_DIR

# Cache for Netflix titles data
_netflix_titles_cache = None


def load_netflix_titles():
    """Load and cache Netflix titles data for enrichment.
    
    Uses augmented_titles.csv as the single source of data with semicolon separator.
    Includes cover_url and tmdb_score fields.
    """
    global _netflix_titles_cache
    if _netflix_titles_cache is not None:
        return _netflix_titles_cache
    
    netflix_titles_path = DATA_DIR / "augmented_titles.csv"
    _netflix_titles_cache = {}
    
    try:
        with open(netflix_titles_path, "r", encoding="utf-8") as f:
            # Use semicolon as delimiter for augmented_titles.csv
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                title = row.get("title", "").strip()
                if title:
                    # Parse tmdb_score, handling empty or invalid values
                    tmdb_score = row.get("tmdb_score", "")
                    try:
                        tmdb_score = float(tmdb_score) if tmdb_score else None
                    except (ValueError, TypeError):
                        tmdb_score = None
                    
                    _netflix_titles_cache[title.lower()] = {
                        "show_id": row.get("show_id", ""),
                        "type": row.get("type", ""),
                        "director": row.get("director", ""),
                        "cast": row.get("cast", ""),
                        "country": row.get("country", ""),
                        "date_added": row.get("date_added", ""),
                        "release_year": row.get("release_year", ""),
                        "rating": row.get("rating", ""),
                        "duration": row.get("duration", ""),
                        "genres": row.get("listed_in", ""),
                        "description": row.get("description", ""),
                        "cover_url": row.get("cover_url", ""),
                        "tmdb_score": tmdb_score,
                        "tmdb_id": row.get("tmdb_id", ""),
                        "imdb_id": row.get("imdb_id", ""),
                    }
        logging.info(f"Loaded {len(_netflix_titles_cache)} Netflix titles for enrichment from augmented_titles.csv")
    except Exception as e:
        logging.error(f"Failed to load Netflix titles: {e}")
        _netflix_titles_cache = {}
    
    return _netflix_titles_cache


def enrich_recommendation(item):
    """Enrich a recommendation item with full details from Netflix titles.
    
    Uses augmented_titles.csv data which includes:
    - cover_url for poster images
    - tmdb_score for ratings (used instead of imdb_score)
    """
    netflix_titles = load_netflix_titles()
    title_lower = item.get("name", "").lower().strip()
    
    def _sanitize_json_value(value, *, default_string=""):
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return default_string
        return value

    # Sanitize fields that can contain NaN
    raw_score = _sanitize_json_value(item.get("raw_score", 0.0), default_string=0.0)
    rating = _sanitize_json_value(item.get("rating", "N/A"), default_string="N/A")
    language = _sanitize_json_value(item.get("language", "N/A"), default_string="N/A")
    # Use tmdb score from item if present, otherwise fall back to imdb for compatibility
    tmdb_score = _sanitize_json_value(item.get("tmdb_score", item.get("imdb", "N/A")), default_string="N/A")
    img = _sanitize_json_value(item.get("img", ""), default_string="")

    # Start with existing data
    enriched = {
        "id": item.get("id"),
        "name": item.get("name"),
        "img": img,
        "imdb": tmdb_score,  # Keep "imdb" key for UI compatibility, but use TMDB score
        "rating": rating,
        "language": language,
        "raw_score": raw_score
    }
    
    # Try to find matching title in Netflix titles data
    title_data = netflix_titles.get(title_lower)
    if title_data:
        # Get TMDB score from title data if available
        title_tmdb_score = title_data.get("tmdb_score")
        if title_tmdb_score is not None:
            enriched["imdb"] = title_tmdb_score
        
        # Get cover image from title data if not already set
        cover_url = title_data.get("cover_url", "")
        if cover_url and not enriched["img"]:
            enriched["img"] = cover_url
        
        enriched.update({
            "type": title_data.get("type", ""),
            "release_year": title_data.get("release_year", ""),
            "duration": title_data.get("duration", ""),
            "genres": title_data.get("genres", ""),
            "description": title_data.get("description", ""),
            "director": title_data.get("director", ""),
            "cast": title_data.get("cast", ""),
            "country": title_data.get("country", ""),
            "tmdb_id": title_data.get("tmdb_id", ""),
            "imdb_id": title_data.get("imdb_id", ""),
        })
    else:
        enriched.update({
            "type": "",
            "release_year": "",
            "duration": "",
            "genres": "",
            "description": "",
            "director": "",
            "cast": "",
            "country": "",
            "tmdb_id": "",
            "imdb_id": "",
        })
    
    return enriched
