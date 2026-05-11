"""New backend entrypoint that keeps legacy routes and adds v1 modules."""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

try:
    from backend import app as app  # legacy app with existing routes
    from backend import db
except Exception as exc:  # pragma: no cover
    raise RuntimeError(f"Failed to import legacy backend app: {exc}") from exc

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.services.job_runner import JobRunner


settings = get_settings()

# Include new modular APIs without breaking existing endpoints.
if not getattr(app.state, "v1_router_included", False):
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    app.state.v1_router_included = True

_job_runner = None


@app.on_event("startup")
def _startup_job_runner():
    global _job_runner
    if db is None:
        print("WARN: MongoDB unavailable, ingest job runner disabled")
        return
    _job_runner = JobRunner(db)
    _job_runner.start()


@app.on_event("shutdown")
def _shutdown_job_runner():
    global _job_runner
    if _job_runner is not None:
        _job_runner.stop()


@app.get("/api/v1/health")
def health():
    return {"ok": True}
