from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import require_permission
from app.services.audit import audit_log

try:
    from backend import papers_col, db
except Exception:  # pragma: no cover
    papers_col = None
    db = None


router = APIRouter()

WORKFLOW_OPTIONS = [
    {"code": "submitted", "name": "已提交"},
    {"code": "initial_review", "name": "初审中"},
    {"code": "peer_review", "name": "外审中"},
    {"code": "revision_required", "name": "需修改"},
    {"code": "accepted", "name": "已录用"},
    {"code": "rejected", "name": "已拒稿"},
    {"code": "published", "name": "已发布"},
]

WORKFLOW_TRANSITIONS = {
    "submitted": ["initial_review", "rejected"],
    "initial_review": ["peer_review", "revision_required", "rejected"],
    "peer_review": ["accepted", "revision_required", "rejected"],
    "revision_required": ["peer_review", "accepted", "rejected"],
    "accepted": ["published", "revision_required"],
    "rejected": [],
    "published": [],
}


class WorkflowTransitionPayload(BaseModel):
    next_status: str = Field(min_length=1)
    comment: str = ""


def _ensure_papers_collection():
    if papers_col is None:
        raise HTTPException(status_code=500, detail="MongoDB papers collection is not available")


def _workflow_name(code: str) -> str:
    for item in WORKFLOW_OPTIONS:
        if item["code"] == code:
            return item["name"]
    return code


def _serialize_paper(doc: dict) -> dict:
    return {
        "paper_id": doc.get("paper_id"),
        "title": doc.get("title", ""),
        "authors": doc.get("authors", []),
        "year": doc.get("year_int") or doc.get("year"),
        "status": doc.get("status", "draft"),
        "workflow_status": doc.get("workflow_status") or "submitted",
        "workflow_status_name": _workflow_name(doc.get("workflow_status") or "submitted"),
        "updated_at": doc.get("updated_at"),
    }


@router.get("/reviews/workflow-options")
def get_workflow_options(_admin=Depends(require_permission("review:view"))):
    return {"items": WORKFLOW_OPTIONS, "transitions": WORKFLOW_TRANSITIONS}


@router.get("/reviews/pipeline")
def list_review_pipeline(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    workflow_status: Optional[str] = Query(default=None),
    _admin=Depends(require_permission("review:view")),
):
    _ensure_papers_collection()
    query = {}
    if keyword:
        query["$or"] = [
            {"title": {"$regex": keyword, "$options": "i"}},
            {"abstract": {"$regex": keyword, "$options": "i"}},
        ]
    if workflow_status:
        query["workflow_status"] = workflow_status

    total = papers_col.count_documents(query)
    cursor = (
        papers_col.find(query)
        .sort("updated_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_serialize_paper(x) for x in cursor]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/reviews/{paper_id}/records")
def list_review_records(paper_id: int, _admin=Depends(require_permission("review:view"))):
    _ensure_papers_collection()
    doc = papers_col.find_one({"paper_id": paper_id}, {"review_records": 1, "workflow_status": 1, "title": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="paper not found")
    return {
        "paper_id": paper_id,
        "title": doc.get("title", ""),
        "workflow_status": doc.get("workflow_status") or "submitted",
        "records": doc.get("review_records") or [],
    }


@router.post("/reviews/{paper_id}/transition")
def transition_workflow(
    paper_id: int,
    payload: WorkflowTransitionPayload,
    admin=Depends(require_permission("review:manage")),
):
    _ensure_papers_collection()
    doc = papers_col.find_one({"paper_id": paper_id})
    if not doc:
        raise HTTPException(status_code=404, detail="paper not found")

    current = doc.get("workflow_status") or "submitted"
    next_status = payload.next_status.strip()
    allowed = WORKFLOW_TRANSITIONS.get(current, [])
    if next_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"workflow transition not allowed: {current} -> {next_status}",
        )

    now = datetime.utcnow()
    review_record = {
        "at": now,
        "actor": admin.get("username"),
        "from_status": current,
        "to_status": next_status,
        "comment": payload.comment.strip(),
    }

    update_doc = {
        "workflow_status": next_status,
        "updated_at": now,
        "updated_by": admin.get("username"),
    }
    if next_status == "published":
        update_doc["status"] = "published"
    elif next_status in {"rejected", "revision_required", "initial_review", "peer_review", "accepted", "submitted"}:
        if doc.get("status") == "published":
            update_doc["status"] = "draft"

    papers_col.update_one(
        {"paper_id": paper_id},
        {
            "$set": update_doc,
            "$push": {"review_records": {"$each": [review_record], "$slice": -200}},
        },
    )

    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="workflow_transition",
        resource="paper",
        resource_id=str(paper_id),
        detail={"from": current, "to": next_status, "comment": payload.comment.strip()},
    )

    return {
        "msg": "updated",
        "paper_id": paper_id,
        "from_status": current,
        "to_status": next_status,
        "status": update_doc.get("status", doc.get("status")),
    }
