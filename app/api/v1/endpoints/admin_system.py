from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_permission

try:
    from backend import db
except Exception:  # pragma: no cover
    db = None


router = APIRouter()


def _ensure_db():
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB is not available")


@router.get("/metrics/overview")
def metrics_overview(_admin=Depends(require_permission("job:view"))):
    _ensure_db()
    papers_col = db["papers"]
    users_col = db["users"]
    jobs_col = db["ingest_jobs"]

    total_papers = papers_col.count_documents({})
    published_papers = papers_col.count_documents({"status": "published"})
    total_users = users_col.count_documents({})
    pending_jobs = jobs_col.count_documents({"status": {"$in": ["queued", "running"]}})
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    new_jobs_24h = jobs_col.count_documents({"created_at": {"$gte": one_day_ago}})
    success_jobs_24h = jobs_col.count_documents({"created_at": {"$gte": one_day_ago}, "status": "success"})
    failed_jobs_24h = jobs_col.count_documents({"created_at": {"$gte": one_day_ago}, "status": "failed"})
    success_rate_24h = round((success_jobs_24h / new_jobs_24h) * 100, 2) if new_jobs_24h else 0

    return {
        "total_papers": total_papers,
        "published_papers": published_papers,
        "total_users": total_users,
        "pending_jobs": pending_jobs,
        "new_jobs_24h": new_jobs_24h,
        "success_jobs_24h": success_jobs_24h,
        "failed_jobs_24h": failed_jobs_24h,
        "success_rate_24h": success_rate_24h,
    }


@router.get("/audit-logs")
def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin=Depends(require_permission("job:view")),
):
    _ensure_db()
    col = db["audit_logs"]
    total = col.count_documents({})
    cursor = (
        col.find({})
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for d in cursor:
        items.append(
            {
                "id": str(d.get("_id")),
                "actor": d.get("actor"),
                "action": d.get("action"),
                "resource": d.get("resource"),
                "resource_id": d.get("resource_id"),
                "detail": d.get("detail", {}),
                "created_at": d.get("created_at"),
            }
        )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/metrics/trend")
def metrics_trend(days: int = Query(default=7, ge=1, le=90), _admin=Depends(require_permission("job:view"))):
    _ensure_db()
    papers_col = db["papers"]
    users_col = db["users"]
    jobs_col = db["ingest_jobs"]
    data = []
    today = datetime.utcnow().date()
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        start = datetime(day.year, day.month, day.day)
        end = start + timedelta(days=1)
        data.append(
            {
                "date": day.isoformat(),
                "new_papers": papers_col.count_documents({"created_at": {"$gte": start, "$lt": end}}),
                "new_users": users_col.count_documents({"created_at": {"$gte": start, "$lt": end}}),
                "new_jobs": jobs_col.count_documents({"created_at": {"$gte": start, "$lt": end}}),
                "success_jobs": jobs_col.count_documents(
                    {"created_at": {"$gte": start, "$lt": end}, "status": "success"}
                ),
            }
        )
    return {"items": data}
