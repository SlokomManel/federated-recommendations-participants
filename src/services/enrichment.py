"""Data enrichment services for recommendations."""

import csv
import math
import logging
from pathlib import Path

from src.config import DATA_DIR

# Cache for Netflix titles data
_netflix_titles_cache = None


def load_netflix_titles():
    """Load and cache Netflix titles data for enrichment."""
    global _netflix_titles_cache
    if _netflix_titles_cache is not None:
        return _netflix_titles_cache
    
    netflix_titles_path = DATA_DIR / "netflix_titles.csv"
    _netflix_titles_cache = {}
    
    try:
        with open(netflix_titles_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title", "").strip()
                if title:
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
                        "description": row.get("description", "")
                    }
        logging.info(f"Loaded {len(_netflix_titles_cache)} Netflix titles for enrichment")
    except Exception as e:
        logging.error(f"Failed to load Netflix titles: {e}")
        _netflix_titles_cache = {}
    
    return _netflix_titles_cache


def enrich_recommendation(item):
    """Enrich a recommendation item with full details from Netflix titles."""
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
    imdb = _sanitize_json_value(item.get("imdb", "N/A"), default_string="N/A")
    img = _sanitize_json_value(item.get("img", ""), default_string="")
    
    # Start with existing data
    enriched = {
        "id": item.get("id"),
        "name": item.get("name"),
        "img": img,
        "imdb": imdb,
        "rating": rating,
        "language": language,
        "raw_score": raw_score
    }
    
    # Try to find matching title in Netflix titles data
    title_data = netflix_titles.get(title_lower)
    if title_data:
        enriched.update({
            "type": title_data.get("type", ""),
            "release_year": title_data.get("release_year", ""),
            "duration": title_data.get("duration", ""),
            "genres": title_data.get("genres", ""),
            "description": title_data.get("description", ""),
            "director": title_data.get("director", ""),
            "cast": title_data.get("cast", ""),
            "country": title_data.get("country", "")
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
            "country": ""
        })
    
    return enriched
