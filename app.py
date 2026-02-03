"""
Netflix Recommendations Participant Application

Entry point for the FastAPI server.

Run:
    uv run python app.py

Or with uvicorn directly:
    uv run uvicorn app:app --host 0.0.0.0 --port 8082 --reload
"""

import sys

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from src.config import APP_NAME, UI_DIR, setup_logging
from src.api.routes import router as api_router
from src.preflight import run_preflight

# Setup logging
setup_logging()

# Run preflight checks - exit if SyftBox not ready
_pf = run_preflight()
if not _pf.ok:
    print("\n" + "=" * 60)
    print("[PRE-FLIGHT CHECK FAILED]")
    print("=" * 60 + "\n")
    print(_pf.message)
    print("\n" + "=" * 60)
    print("The app cannot start without SyftBox properly configured.")
    print("Please follow the instructions above, then re-run the app.")
    print("=" * 60 + "\n")
    sys.exit(1)

# Initialize FastSyftBox app
from fastsyftbox import FastSyftBox
from syft_core import SyftClientConfig

_cfg = SyftClientConfig.load()
app = FastSyftBox(
    app_name=APP_NAME,
    syftbox_config=_cfg,
    syftbox_endpoint_tags=["syftbox"],
    include_syft_openapi=True,
)

# Mount static UI folder
if UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_DIR), html=True), name="static")

# Include API routes
app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to the main UI."""
    return RedirectResponse(url="/static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8082)
