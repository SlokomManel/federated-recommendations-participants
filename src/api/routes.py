"""API route handlers."""

import csv
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse

from src.config import APP_NAME, AGGREGATOR_DATASITE
from src.core import (
    client,
    get_private_path,
    setup_environment,
)
from src.services.enrichment import enrich_recommendation
from src.services.io import recommendations_exist, load_recommendations
from src.services.recommendations import (
    run_recommendation_computation,
    get_computation_status,
    set_pending_click_history,
)
from src.services.federated_learning import (
    run_fine_tuning,
    run_full_fl_workflow,
    get_fl_status,
    check_fine_tuning_needed,
    check_viewing_history_exists,
)

router = APIRouter(prefix="/api")


def _ensure_csv_has_header(csv_file_path: Path, header_row: list[str]) -> None:
    """
    Ensure a CSV exists and has the expected header as the first row.

    If the file doesn't exist, it is created with the header.
    If it exists but is empty, it is overwritten with the header.
    If it exists but has a different first row, the file is rewritten with the
    expected header prepended (keeping existing content).
    """
    csv_file_path.parent.mkdir(parents=True, exist_ok=True)

    if not csv_file_path.exists():
        with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header_row)
        return

    # Read the first row (if any) and the remainder verbatim.
    with open(csv_file_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        first_row = next(reader, None)
        rest = f.read()

    # Empty file: overwrite with header
    if not first_row:
        with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header_row)
        return

    # Already correct
    if first_row == header_row:
        return

    # Rewrite with header + original content (including original first line)
    with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(header_row)
        f.write(",".join(first_row) + "\n")
        f.write(rest)


@router.get("/health")
async def api_health():
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "app_name": APP_NAME,
        "timestamp": datetime.now().isoformat()
    })


@router.get("/data/status")
async def api_data_status():
    """Check if Netflix viewing history exists."""
    data_status = check_viewing_history_exists()
    return JSONResponse({
        "has_data": data_status["exists"],
        "source": data_status["source"],
        "path": data_status["path"],
        "timestamp": datetime.now().isoformat()
    })


@router.post("/data/upload")
async def api_upload_history(file: UploadFile = File(...)):
    """
    Upload Netflix viewing history CSV.
    
    Validates the CSV has a "Title" column and saves it to the private path.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            return JSONResponse({
                "status": "error",
                "message": "File must be a CSV"
            }, status_code=400)
        
        # Read file content and normalize line endings
        content = await file.read()
        content_str = content.decode('utf-8')
        # Normalize line endings (Windows \r\n -> Unix \n)
        content_str = content_str.replace('\r\n', '\n').replace('\r', '\n')
        
        # Validate CSV has Title column
        lines = [line for line in content_str.strip().split('\n') if line.strip()]
        if not lines:
            return JSONResponse({
                "status": "error",
                "message": "CSV file is empty"
            }, status_code=400)
        
        # Parse header
        reader = csv.reader([lines[0]])
        header = next(reader)
        header_lower = [col.lower().strip() for col in header]
        
        if 'title' not in header_lower:
            return JSONResponse({
                "status": "error",
                "message": "CSV must have a 'Title' column. Netflix viewing history format expected."
            }, status_code=400)
        
        # Save to private path (with cleaned content - no empty lines)
        private_path = get_private_path()
        private_path.mkdir(parents=True, exist_ok=True)
        
        save_path = private_path / "NetflixViewingHistory.csv"
        # Write cleaned lines (no empty lines, normalized line endings)
        cleaned_content = '\n'.join(lines)
        with open(save_path, 'w', encoding='utf-8', newline='') as f:
            f.write(cleaned_content)
        
        # Count rows (excluding header)
        row_count = len(lines) - 1
        
        logging.info(f"Uploaded Netflix viewing history: {save_path} ({row_count} entries)")
        
        return JSONResponse({
            "status": "success",
            "message": f"Successfully uploaded {row_count} viewing history entries",
            "path": str(save_path),
            "row_count": row_count,
            "timestamp": datetime.now().isoformat()
        })
        
    except UnicodeDecodeError:
        return JSONResponse({
            "status": "error",
            "message": "Could not decode file. Please ensure it's a valid UTF-8 CSV."
        }, status_code=400)
    except Exception as e:
        logging.error(f"Upload error: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@router.get("/status")
async def api_status():
    """Check if recommendations are available and computation status."""
    has_recommendations = recommendations_exist()
    computation_status = get_computation_status()
    fl_status = get_fl_status()
    data_status = check_viewing_history_exists()
    has_viewing_history = data_status["exists"]
    
    # FL workflow status takes precedence over simple computation
    if fl_status["status"] in ["running", "fine_tuning"]:
        return JSONResponse({
            "status": fl_status["status"],
            "has_recommendations": has_recommendations,
            "has_viewing_history": has_viewing_history,
            "message": fl_status["message"],
            "last_updated": fl_status["last_updated"]
        })
    
    # Check for FL errors
    if fl_status["status"] == "error":
        return JSONResponse({
            "status": "error",
            "error_type": fl_status.get("error_type", "error"),
            "has_recommendations": has_recommendations,
            "has_viewing_history": has_viewing_history,
            "message": fl_status["message"],
            "last_updated": fl_status["last_updated"]
        })
    
    if computation_status["status"] == "computing":
        return JSONResponse({
            "status": "computing",
            "has_recommendations": has_recommendations,
            "has_viewing_history": has_viewing_history,
            "message": computation_status["message"],
            "last_updated": computation_status["last_updated"]
        })
    
    # Check for computation errors
    if computation_status["status"] == "error":
        return JSONResponse({
            "status": "error",
            "error_type": computation_status.get("error_type", "error"),
            "has_recommendations": has_recommendations,
            "has_viewing_history": has_viewing_history,
            "message": computation_status["message"],
            "last_updated": computation_status["last_updated"]
        })
    
    if has_recommendations:
        return JSONResponse({
            "status": "ready",
            "has_recommendations": True,
            "has_viewing_history": has_viewing_history,
            "message": "Recommendations are available",
            "last_updated": computation_status.get("last_updated")
        })
    else:
        return JSONResponse({
            "status": "pending",
            "has_recommendations": False,
            "has_viewing_history": has_viewing_history,
            "message": "No recommendations available. Trigger computation." if has_viewing_history else "No viewing history found. Please upload your Netflix data.",
            "last_updated": None
        })


@router.get("/recommendations")
async def api_recommendations():
    """Fetch current recommendations with full details."""
    if not recommendations_exist():
        return JSONResponse({
            "error": "No recommendations available",
            "status": "pending"
        }, status_code=404)
    
    try:
        raw_recommends, reranked_recommends = load_recommendations()
        
        enriched_raw = [enrich_recommendation(item) for item in raw_recommends]
        enriched_reranked = [enrich_recommendation(item) for item in reranked_recommends]
        
        # Debug: log sample raw_score values to help diagnose UI percentage display
        try:
            sample_raw_scores = [ir.get('raw_score') for ir in enriched_raw[:10]]
            sample_counts = [ir.get('count') for ir in enriched_raw[:10]]
            logging.debug(f"Returning recommendations (sample raw_scores): {sample_raw_scores}")
            logging.debug(f"Returning recommendations (sample counts): {sample_counts}")
        except Exception as e:
            logging.debug(f"Could not log sample scores: {e}")
        
        return JSONResponse({
            "status": "success",
            "raw_recommendations": enriched_raw,
            "reranked_recommendations": enriched_reranked,
            "user_email": client.email,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error fetching recommendations: {e}")
        return JSONResponse({
            "error": str(e),
            "status": "error"
        }, status_code=500)


@router.get("/movie/{movie_id}")
async def api_movie_details(movie_id: int):
    """
    Fetch enriched details for a specific movie by ID.
    
    Used by the modal to display full details when clicking on history items.
    """
    if not recommendations_exist():
        return JSONResponse({
            "error": "No recommendations available",
            "status": "pending"
        }, status_code=404)
    
    try:
        raw_recommends, reranked_recommends = load_recommendations()
        
        # Search in both lists for the movie
        item = None
        for rec in raw_recommends:
            if rec.get("id") == movie_id:
                item = rec
                break
        
        if not item:
            for rec in reranked_recommends:
                if rec.get("id") == movie_id:
                    item = rec
                    break
        
        if not item:
            return JSONResponse({
                "error": f"Movie with ID {movie_id} not found",
                "status": "not_found"
            }, status_code=404)
        
        # Enrich the item with full details
        enriched_item = enrich_recommendation(item)
        
        return JSONResponse({
            "status": "success",
            "item": enriched_item,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error fetching movie details: {e}")
        return JSONResponse({
            "error": str(e),
            "status": "error"
        }, status_code=500)


@router.post("/recommendations/compute")
async def api_compute_recommendations(background_tasks: BackgroundTasks, data: dict = None):
    """Trigger recommendation computation in the background."""
    status = get_computation_status()
    
    if status["status"] == "computing":
        return JSONResponse({
            "status": "already_computing",
            "message": "Computation is already in progress",
            "last_updated": status["last_updated"]
        })
    
    click_history = []
    if data and data.get("click_history"):
        click_history = data.get("click_history", [])
        logging.info(f"Received {len(click_history)} items from click history")
    
    set_pending_click_history(click_history)
    background_tasks.add_task(run_recommendation_computation)
    
    return JSONResponse({
        "status": "started",
        "message": "Recommendation computation started in background",
        "click_history_items": len(click_history),
        "last_updated": datetime.now().isoformat()
    })


@router.post("/watchlist")
async def api_watchlist(data: dict):
    """Record will/won't watch action for a recommendation."""
    try:
        title = data.get("title", "")
        action = data.get("action", "")
        use_reranked = data.get("useReranked", False)
        rank = data.get("rank", None)
        page = data.get("page", 1)
        visible_items = data.get("visible_items", [])
        
        if action not in ["will_watch", "wont_watch"]:
            return JSONResponse({
                "error": "Invalid action. Must be 'will_watch' or 'wont_watch'",
                "status": "error"
            }, status_code=400)
        
        timestamp = datetime.now().isoformat()
        item_from_column = "Re-ranked" if use_reranked else "Unprocessed"
        
        row = [timestamp, client.email, rank, page, visible_items, item_from_column, title, action]
        
        # NOTE: Do NOT write into the aggregator's `shared/` folder, since that is publicly readable.
        # Instead write into our own restricted app_data folder with permissions granting the aggregator read access.
        _, restricted_public_folder, _ = setup_environment("profile_0")
        csv_file_path = restricted_public_folder / "interaction_logs" / "recommendations.csv"
        _ensure_csv_has_header(
            csv_file_path,
            ["timestamp", "user", "rank", "page", "visible_items", "column", "title", "action"],
        )
        
        with open(csv_file_path, "a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        
        logging.info(f"Watchlist action recorded: {action} for '{title}'")
        
        return JSONResponse({
            "status": "success",
            "message": f"Recorded '{action}' for '{title}'",
            "timestamp": timestamp
        })
        
    except Exception as e:
        logging.error(f"Error recording watchlist action: {e}")
        return JSONResponse({
            "error": str(e),
            "status": "error"
        }, status_code=500)


@router.get("/user")
async def api_user():
    """Get current user information."""
    return JSONResponse({
        "email": client.email,
        "app_name": APP_NAME,
        "timestamp": datetime.now().isoformat()
    })


@router.post("/choice")
async def api_choice(data: dict):
    """Record user's choice from recommendations."""
    try:
        raw_recommends, reranked_recommends = load_recommendations()
        timestamp = datetime.now().isoformat()
        
        page = data.get('page', 1)
        rank = data.get("rank", None)
        visible_items = data.get('visible_items', [])
        
        if data.get('column') == 1:
            column = "Unprocessed"
            title = next((item["name"] for item in raw_recommends if item["id"] == data.get('id')), None)
        else:
            column = "Re-ranked"
            title = next((item["name"] for item in reranked_recommends if item["id"] == data.get('id')), None)

        # Keep a consistent schema with `/watchlist` rows by filling `action`.
        row = [timestamp, client.email, rank, page, visible_items, column, title, "clicked"]

        # Store privately (restricted to aggregator-read) instead of publishing to aggregator shared.
        _, restricted_public_folder, _ = setup_environment("profile_0")
        csv_file_path = restricted_public_folder / "interaction_logs" / "recommendations.csv"
        _ensure_csv_has_header(
            csv_file_path,
            ["timestamp", "user", "rank", "page", "visible_items", "column", "title", "action"],
        )

        logging.info(f"Recording choice: {title} from {column} (rank {rank}, page {page})")
        with open(csv_file_path, "a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        return JSONResponse({
            "status": "success",
            "message": f"Received choice from {column} (ID: {data.get('id')} - {title}, page {page})"
        })
        
    except Exception as e:
        logging.error(f"Error recording choice: {e}")
        return JSONResponse({
            "error": str(e),
            "status": "error"
        }, status_code=500)


@router.post("/feedback")
async def api_feedback(data: dict):
    """Submit user feedback (rating and optional text)."""
    try:
        rating = data.get("rating", 0)
        feedback_text = data.get("feedback", "")
        timestamp = data.get("timestamp", datetime.now().isoformat())
        
        if not 1 <= rating <= 5:
            return JSONResponse({
                "error": "Rating must be between 1 and 5",
                "status": "error"
            }, status_code=400)
        
        row = [timestamp, client.email, rating, feedback_text]
        
        # Store privately (restricted to aggregator-read) instead of publishing to aggregator shared.
        _, restricted_public_folder, _ = setup_environment("profile_0")
        csv_file_path = restricted_public_folder / "interaction_logs" / "feedback.csv"
        
        import os
        if not csv_file_path.exists():
            os.makedirs(csv_file_path.parent, exist_ok=True)
            with open(csv_file_path, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "user", "rating", "feedback"])
        
        with open(csv_file_path, "a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        
        logging.info(f"Feedback recorded: {rating} stars from {client.email}")
        
        return JSONResponse({
            "status": "success",
            "message": "Thank you for your feedback!"
        })
        
    except Exception as e:
        logging.error(f"Error recording feedback: {e}")
        return JSONResponse({
            "error": str(e),
            "status": "error"
        }, status_code=500)


@router.post("/opt-out")
async def api_opt_out(data: dict):
    """
    Record an opt-out interaction (optional reason/user_message).

    Stored privately in the restricted interaction logs folder for aggregator read access.
    """
    try:
        reason = data.get("reason", "") or ""
        user_message = data.get("user_message", "") or ""
        timestamp = data.get("timestamp", datetime.now().isoformat())

        row = [timestamp, client.email, reason, user_message]

        # Store privately (restricted to aggregator-read) instead of publishing to aggregator shared.
        _, restricted_public_folder, _ = setup_environment("profile_0")
        csv_file_path = restricted_public_folder / "interaction_logs" / "opt_out.csv"
        _ensure_csv_has_header(
            csv_file_path,
            ["timestamp", "user", "reason", "user_message"],
        )

        with open(csv_file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        logging.info(f"Opt-out recorded for {client.email}")

        return JSONResponse({
            "status": "success",
            "message": "Opt-out recorded"
        })
    except Exception as e:
        logging.error(f"Error recording opt-out: {e}")
        return JSONResponse({
            "error": str(e),
            "status": "error"
        }, status_code=500)


# Settings Tracking Endpoint

@router.post("/settings/log")
async def api_settings_log(data: dict):
    """
    Log user settings interaction to CSV for aggregator analytics.
    
    Called when user toggles any setting (not on page load).
    Records the full current state of all settings.
    
    Request body:
        showMoreDetails (bool): Show rating, year, genre under cards
        useReranked (bool): Use re-ranked recommendations
        showWhyRecommended (bool): Show "why recommended" in modal
        enableWatchlist (bool): Enable will/won't watch buttons
        enableBlockItems (bool): Enable "don't recommend again" feature
        showActivityCharts (bool): Show charts on profile page
        showWatchlistStatus (bool): Show will/won't watch badges
    """
    try:
        timestamp = datetime.now().isoformat()
        
        # Extract settings values (default to True except useReranked)
        settings_values = {
            "showMoreDetails": data.get("showMoreDetails", True),
            "useReranked": data.get("useReranked", False),
            "showWhyRecommended": data.get("showWhyRecommended", True),
            "enableWatchlist": data.get("enableWatchlist", True),
            "enableBlockItems": data.get("enableBlockItems", True),
            "showActivityCharts": data.get("showActivityCharts", True),
            "showWatchlistStatus": data.get("showWatchlistStatus", True),
        }
        
        row = [
            timestamp,
            client.email,
            settings_values["showMoreDetails"],
            settings_values["useReranked"],
            settings_values["showWhyRecommended"],
            settings_values["enableWatchlist"],
            settings_values["enableBlockItems"],
            settings_values["showActivityCharts"],
            settings_values["showWatchlistStatus"],
        ]
        
        # Store privately (restricted to aggregator-read)
        _, restricted_public_folder, _ = setup_environment("profile_0")
        csv_file_path = restricted_public_folder / "interaction_logs" / "settings.csv"
        _ensure_csv_has_header(
            csv_file_path,
            [
                "timestamp", "user",
                "showMoreDetails", "useReranked", "showWhyRecommended",
                "enableWatchlist", "enableBlockItems", "showActivityCharts",
                "showWatchlistStatus"
            ],
        )
        
        with open(csv_file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        
        logging.info(f"Settings logged for {client.email}")
        
        return JSONResponse({
            "status": "success",
            "message": "Settings logged",
            "timestamp": timestamp
        })
    except Exception as e:
        logging.error(f"Error logging settings: {e}")
        return JSONResponse({
            "error": str(e),
            "status": "error"
        }, status_code=500)


# Federated Learning Endpoints

@router.get("/fl/status")
async def api_fl_status():
    """Get federated learning status."""
    status = get_fl_status()
    needs_training = check_fine_tuning_needed()
    
    return JSONResponse({
        **status,
        "needs_fine_tuning": needs_training,
        "timestamp": datetime.now().isoformat()
    })


@router.get("/fl/global-v-info")
async def api_global_v_info():
    """
    Get information about the global model file (global_V.npy).
    
    Used by the frontend to detect when the aggregator has updated the global model,
    so it can auto-trigger a refresh of recommendations.
    
    Returns:
        exists: Whether the global_V.npy file exists
        last_modified: ISO timestamp of the file's last modification time
        path: File path (for debugging)
    """
    profile = "profile_0"
    restricted_shared_folder, _, _ = setup_environment(profile)
    global_v_path = restricted_shared_folder / "global_V.npy"
    
    if global_v_path.exists():
        mtime = global_v_path.stat().st_mtime
        return JSONResponse({
            "exists": True,
            "last_modified": datetime.fromtimestamp(mtime).isoformat(),
            "path": str(global_v_path),
            "timestamp": datetime.now().isoformat()
        })
    
    return JSONResponse({
        "exists": False,
        "last_modified": None,
        "path": str(global_v_path),
        "timestamp": datetime.now().isoformat()
    })


@router.post("/fl/fine-tune")
async def api_fine_tune(background_tasks: BackgroundTasks, data: dict = None):
    """Trigger participant fine-tuning in the background."""
    status = get_fl_status()
    
    if status["status"] in ["fine_tuning", "running"]:
        return JSONResponse({
            "status": "already_running",
            "message": "Fine-tuning or FL workflow is already in progress",
            "last_updated": status["last_updated"]
        })
    
    epsilon = 1.0
    profile = "profile_0"
    if data:
        epsilon = data.get("epsilon", 1.0)
        profile = data.get("profile", "profile_0")
    
    background_tasks.add_task(run_fine_tuning, profile, epsilon)
    
    return JSONResponse({
        "status": "started",
        "message": "Fine-tuning started in background",
        "profile": profile,
        "epsilon": epsilon,
        "timestamp": datetime.now().isoformat()
    })


@router.post("/fl/run")
async def api_run_fl_workflow(background_tasks: BackgroundTasks, data: dict = None):
    """
    Run the complete federated learning workflow:
    1. Setup environment
    2. Prepare data from viewing history (augmented with click history)
    3. Run fine-tuning
    4. Generate recommendations
    
    Request body:
        profile (str): User profile identifier (default: "profile_0")
        epsilon (float): Privacy budget (default: 1.0)
        click_history (list): Optional list of clicked items to enhance training
    """
    epsilon = 1.0
    profile = "profile_0"
    click_history = None
    
    if data:
        epsilon = data.get("epsilon", 1.0)
        profile = data.get("profile", "profile_0")
        click_history = data.get("click_history", None)
    
    # Pre-check: Verify viewing history exists before starting workflow
    data_status = check_viewing_history_exists(profile)
    if not data_status["exists"]:
        return JSONResponse({
            "status": "no_viewing_history",
            "message": "No viewing history found. Please upload your Netflix viewing history first.",
            "timestamp": datetime.now().isoformat()
        }, status_code=400)
    
    status = get_fl_status()
    
    if status["status"] in ["fine_tuning", "running"]:
        return JSONResponse({
            "status": "already_running",
            "message": "FL workflow is already in progress",
            "last_updated": status["last_updated"]
        })
    
    click_count = len(click_history) if click_history else 0
    
    background_tasks.add_task(run_full_fl_workflow, profile, epsilon, click_history)
    
    return JSONResponse({
        "status": "started",
        "message": f"Full FL workflow started in background with {click_count} click history items",
        "profile": profile,
        "epsilon": epsilon,
        "click_history_count": click_count,
        "timestamp": datetime.now().isoformat()
    })
