import os
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.core.security import require_permission
from app.services.audit import audit_log

try:
    from backend import db
except Exception:  # pragma: no cover
    db = None


router = APIRouter()


class JobCreate(BaseModel):
    type: str = Field(default="import", pattern="^(import|reindex|summary)$")
    payload: dict = Field(default_factory=dict)


class JobStatusUpdate(BaseModel):
    status: str = Field(pattern="^(queued|running|success|failed|canceled)$")
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    error: Optional[str] = None


def _jobs_col():
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB is not available")
    return db["ingest_jobs"]


def _uploads_dir() -> str:
    root_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    )
    target = os.path.join(root_dir, "data", "uploads")
    os.makedirs(target, exist_ok=True)
    return target


def _sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name or "upload.bib")
    return safe[-120:] if len(safe) > 120 else safe


def _serialize(doc: dict) -> dict:
    return {
        "job_id": str(doc.get("_id")),
        "type": doc.get("type"),
        "status": doc.get("status"),
        "progress": doc.get("progress", 0),
        "payload": doc.get("payload", {}),
        "error": doc.get("error"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "created_by": doc.get("created_by"),
        "result": doc.get("result"),
        "logs": doc.get("logs", []),
    }


@router.get("/jobs")
def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    job_type: Optional[str] = Query(default=None),
    _admin=Depends(require_permission("job:view")),
):
    query = {}
    if status:
        query["status"] = status
    if job_type:
        query["type"] = job_type

    col = _jobs_col()
    total = col.count_documents(query)
    cursor = col.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = [_serialize(d) for d in cursor]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.post("/jobs")
def create_job(payload: JobCreate, admin=Depends(require_permission("job:create"))):
    col = _jobs_col()
    now = datetime.utcnow()
    doc = {
        "type": payload.type,
        "status": "queued",
        "progress": 0,
        "payload": payload.payload,
        "error": None,
        "logs": [f"{datetime.utcnow().isoformat()} | 任务已创建"],
        "created_at": now,
        "updated_at": now,
        "created_by": admin.get("username"),
    }
    result = col.insert_one(doc)
    doc["_id"] = result.inserted_id
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="create",
        resource="job",
        resource_id=str(result.inserted_id),
        detail={"type": payload.type},
    )
    return {"msg": "created", "job": _serialize(doc)}


@router.post("/jobs/import-upload")
async def create_import_job_by_upload(file: UploadFile = File(...), admin=Depends(require_permission("job:create"))):
    filename = file.filename or "upload.bib"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".bib", ".csv", ".json"}:
        raise HTTPException(status_code=400, detail="仅支持 .bib/.csv/.json 文件")

    now = datetime.utcnow()
    safe_name = _sanitize_filename(filename)
    save_name = f"{now.strftime('%Y%m%d_%H%M%S_%f')}_{safe_name}"
    abs_path = os.path.join(_uploads_dir(), save_name)
    rel_path = os.path.join("data", "uploads", save_name).replace("\\", "/")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    with open(abs_path, "wb") as f:
        f.write(content)

    col = _jobs_col()
    doc = {
        "type": "import",
        "status": "queued",
        "progress": 0,
        "payload": {"source": rel_path, "original_filename": filename},
        "error": None,
        "logs": [f"{datetime.utcnow().isoformat()} | 文件已上传 {filename}"],
        "created_at": now,
        "updated_at": now,
        "created_by": admin.get("username"),
    }
    result = col.insert_one(doc)
    doc["_id"] = result.inserted_id
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="create",
        resource="job",
        resource_id=str(result.inserted_id),
        detail={"type": "import", "source": rel_path, "upload": True},
    )
    return {"msg": "created", "job": _serialize(doc)}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, _admin=Depends(require_permission("job:view"))):
    from bson import ObjectId

    col = _jobs_col()
    try:
        obj_id = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job id")

    doc = col.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": _serialize(doc)}


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str, admin=Depends(require_permission("job:retry"))):
    from bson import ObjectId

    col = _jobs_col()
    try:
        obj_id = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job id")

    current = col.find_one({"_id": obj_id})
    if not current:
        raise HTTPException(status_code=404, detail="Job not found")
    if current.get("status") not in {"failed", "canceled"}:
        raise HTTPException(status_code=400, detail="仅失败或取消的任务可重试")

    logs = current.get("logs", [])
    logs.append(f"{datetime.utcnow().isoformat()} | 用户 {admin.get('username')} 触发重试")
    col.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "status": "queued",
                "progress": 0,
                "error": None,
                "logs": logs[-500:],
                "updated_at": datetime.utcnow(),
                "updated_by": admin.get("username"),
            }
        },
    )
    new_doc = col.find_one({"_id": obj_id})
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="retry",
        resource="job",
        resource_id=job_id,
    )
    return {"msg": "retried", "job": _serialize(new_doc)}


@router.put("/jobs/{job_id}/status")
def update_job_status(job_id: str, payload: JobStatusUpdate, admin=Depends(require_permission("job:retry"))):
    from bson import ObjectId

    col = _jobs_col()
    try:
        obj_id = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job id")

    current = col.find_one({"_id": obj_id})
    if not current:
        raise HTTPException(status_code=404, detail="Job not found")

    update_doc = {
        "status": payload.status,
        "updated_at": datetime.utcnow(),
        "updated_by": admin.get("username"),
    }
    if payload.progress is not None:
        update_doc["progress"] = payload.progress
    if payload.error is not None:
        update_doc["error"] = payload.error

    col.update_one({"_id": obj_id}, {"$set": update_doc})
    new_doc = col.find_one({"_id": obj_id})
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="update_status",
        resource="job",
        resource_id=job_id,
        detail={"status": payload.status, "progress": payload.progress},
    )
    return {"msg": "updated", "job": _serialize(new_doc)}
