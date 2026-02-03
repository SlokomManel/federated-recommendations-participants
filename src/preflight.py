"""
SyftBox + app configuration preflight checks.

Used by:
- install scripts (fail fast with actionable instructions)
- runtime endpoints (surface friendly diagnostics instead of hard crashes)
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PreflightError(RuntimeError):
    """Raised when required prerequisites are not met."""


_EMAIL_LIKE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_syft_user(value: str | None) -> bool:
    # SyftPermission currently accepts either an email-like identifier or '*'.
    if value is None:
        return False
    v = value.strip().strip('"').strip("'")
    return v == "*" or bool(_EMAIL_LIKE_RE.match(v))


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    checks: dict[str, Any]
    message: str


def run_preflight() -> PreflightResult:
    """
    Validate critical prerequisites.

    This intentionally does NOT try to install or start SyftBox; it only detects
    common failure modes and returns high-quality guidance.
    """
    checks: dict[str, Any] = {}

    # Load .env if present (so install-time checks match runtime behavior).
    try:
        from dotenv import load_dotenv  # type: ignore

        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            checks["dotenv_loaded"] = str(env_path)
        else:
            checks["dotenv_loaded"] = None
    except Exception:
        # Not fatal; environment variables may still be set by the user/shell.
        checks["dotenv_loaded"] = "unavailable"

    # ---- App env checks
    aggregator = os.getenv("AGGREGATOR_DATASITE")
    checks["AGGREGATOR_DATASITE"] = aggregator
    if not _is_valid_syft_user(aggregator):
        return PreflightResult(
            ok=False,
            checks=checks,
            message=(
                "Missing or invalid `AGGREGATOR_DATASITE`.\n\n"
                "Fix:\n"
                "- Open `.env` and set `AGGREGATOR_DATASITE` to the aggregator's datasite email.\n"
                "- If you don't have it, ask the organizer for the correct value.\n\n"
                "Why:\n"
                "- The app must grant the aggregator read access to your restricted folder. "
                "If `AGGREGATOR_DATASITE` is empty, SyftBox permission rules fail to parse."
            ),
        )

    # ---- SyftBox checks (via syft-core)
    checks["syftbox_cli_found"] = bool(shutil.which("syftbox"))
    try:
        from syft_core import SyftClientConfig  # type: ignore
    except Exception as e:  # pragma: no cover
        checks["syft_core_import_error"] = str(e)
        return PreflightResult(
            ok=False,
            checks=checks,
            message=(
                "Python dependencies are not installed correctly (could not import `syft_core`).\n\n"
                "Fix:\n"
                "- Re-run the install script.\n"
                "- If it still fails, delete `.venv` and re-run the install script.\n"
            ),
        )

    try:
        cfg = SyftClientConfig.load()
        # Best-effort: common symptom in your reports.
        email = getattr(cfg, "email", None)
        checks["syftbox_config_loaded"] = True
        checks["syftbox_email"] = email
        if not _is_valid_syft_user(email):
            return PreflightResult(
                ok=False,
                checks=checks,
                message=(
                    "SyftBox config was found, but your SyftBox identity looks incomplete "
                    "(missing/invalid email).\n\n"
                    "Fix:\n"
                    "- Start SyftBox (desktop app or CLI) and complete the setup/login flow.\n"
                    "- Then close and re-open your terminal and re-run the install/start command.\n"
                ),
            )
    except Exception as e:
        checks["syftbox_config_loaded"] = False
        checks["syftbox_config_error"] = str(e)

        # Helpful hint for the specific failure shown in your screenshots.
        hint = ""
        if "Config file not found" in str(e) or "Failed to load config" in str(e):
            hint = (
                "\n\nCommon causes:\n"
                "- SyftBox is not installed.\n"
                "- SyftBox is installed but has never been opened / setup was not completed.\n"
                "- You installed SyftBox, but this terminal session can't see its environment yet "
                "(try closing and reopening the terminal).\n"
            )

        return PreflightResult(
            ok=False,
            checks=checks,
            message=(
                "SyftBox is not ready (could not load SyftBox client config).\n\n"
                "Fix:\n"
                "- Install SyftBox: https://syftbox.net/\n"
                "- Start SyftBox and complete setup/login.\n"
                "- Keep SyftBox running while using this app.\n"
                "- Then re-run the install/start command.\n"
                f"{hint}"
                "\nDetails:\n"
                f"- {e}"
            ),
        )

    return PreflightResult(
        ok=True,
        checks=checks,
        message="Preflight OK",
    )


def require_preflight() -> PreflightResult:
    """Run preflight and raise PreflightError with the user-facing message on failure."""
    result = run_preflight()
    if not result.ok:
        raise PreflightError(result.message)
    return result


def _main() -> None:  # pragma: no cover
    result = run_preflight()
    if result.ok:
        print("Preflight OK")
        return
    print("\n[PRE-FLIGHT CHECK FAILED]\n")
    print(result.message)
    raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    _main()

