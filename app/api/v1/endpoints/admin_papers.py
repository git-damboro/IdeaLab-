import os
import sys
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import require_permission
from app.services.audit import audit_log

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

try:
    from backend import papers_col, db
except Exception:  # pragma: no cover
    papers_col = None
    db = None


router = APIRouter()


class PaperCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    month: Optional[str] = None
    venue: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    status: str = "draft"


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[list[str]] = None
    year: Optional[int] = None
    month: Optional[str] = None
    venue: Optional[str] = None
    keywords: Optional[list[str]] = None
    status: Optional[str] = None


def _serialize_paper(doc: dict) -> dict:
    return {
        "paper_id": doc.get("paper_id"),
        "title": doc.get("title", ""),
        "abstract": doc.get("abstract", ""),
        "authors": doc.get("authors", []),
        "year": doc.get("year_int") or doc.get("year"),
        "month": doc.get("month"),
        "venue": doc.get("booktitle") or doc.get("venue"),
        "keywords": doc.get("keywords", []),
        "status": doc.get("status", "published"),
        "workflow_status": doc.get("workflow_status", "submitted"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def _ensure_papers_collection():
    if papers_col is None:
        raise HTTPException(status_code=500, detail="MongoDB papers collection is not available")


def _next_paper_id() -> int:
    _ensure_papers_collection()
    latest = papers_col.find_one({}, sort=[("paper_id", -1)], projection={"paper_id": 1})
    if not latest or latest.get("paper_id") is None:
        return 1
    return int(latest["paper_id"]) + 1


@router.get("")
def list_papers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    _admin=Depends(require_permission("paper:view")),
):
    _ensure_papers_collection()
    query = {}
    if keyword:
        query["$or"] = [
            {"title": {"$regex": keyword, "$options": "i"}},
            {"abstract": {"$regex": keyword, "$options": "i"}},
        ]
    if status:
        query["status"] = status

    total = papers_col.count_documents(query)
    cursor = (
        papers_col.find(query)
        .sort("paper_id", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_serialize_paper(d) for d in cursor]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/{paper_id}")
def get_paper_detail(paper_id: int, _admin=Depends(require_permission("paper:view"))):
    _ensure_papers_collection()
    doc = papers_col.find_one({"paper_id": paper_id})
    if not doc:
        raise HTTPException(status_code=404, detail="paper not found")
    return {"paper": _serialize_paper(doc)}


@router.post("")
def create_paper(payload: PaperCreate, admin=Depends(require_permission("paper:create"))):
    _ensure_papers_collection()
    now = datetime.utcnow()
    paper_id = _next_paper_id()
    doc = {
        "paper_id": paper_id,
        "title": payload.title.strip(),
        "abstract": payload.abstract.strip(),
        "authors": payload.authors,
        "year_int": payload.year or 0,
        "month": payload.month or "",
        "booktitle": payload.venue or "",
        "keywords": payload.keywords,
        "status": payload.status,
        "workflow_status": "submitted",
        "review_records": [],
        "created_by": admin.get("username"),
        "updated_by": admin.get("username"),
        "created_at": now,
        "updated_at": now,
    }
    papers_col.insert_one(doc)
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="create",
        resource="paper",
        resource_id=str(paper_id),
        detail={"title": doc["title"], "status": doc["status"]},
    )
    return {"msg": "created", "paper": _serialize_paper(doc)}


@router.put("/{paper_id}")
def update_paper(paper_id: int, payload: PaperUpdate, admin=Depends(require_permission("paper:update"))):
    _ensure_papers_collection()
    current = papers_col.find_one({"paper_id": paper_id})
    if not current:
        raise HTTPException(status_code=404, detail="paper not found")

    update_fields = {}
    if payload.title is not None:
        update_fields["title"] = payload.title.strip()
    if payload.abstract is not None:
        update_fields["abstract"] = payload.abstract.strip()
    if payload.authors is not None:
        update_fields["authors"] = payload.authors
    if payload.year is not None:
        update_fields["year_int"] = payload.year
    if payload.month is not None:
        update_fields["month"] = payload.month
    if payload.venue is not None:
        update_fields["booktitle"] = payload.venue
    if payload.keywords is not None:
        update_fields["keywords"] = payload.keywords
    if payload.status is not None:
        update_fields["status"] = payload.status

    update_fields["updated_at"] = datetime.utcnow()
    update_fields["updated_by"] = admin.get("username")

    papers_col.update_one({"paper_id": paper_id}, {"$set": update_fields})
    new_doc = papers_col.find_one({"paper_id": paper_id})
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="update",
        resource="paper",
        resource_id=str(paper_id),
        detail={"fields": list(update_fields.keys())},
    )
    return {"msg": "updated", "paper": _serialize_paper(new_doc)}


@router.post("/{paper_id}/publish")
def publish_paper(paper_id: int, admin=Depends(require_permission("paper:publish"))):
    _ensure_papers_collection()
    current = papers_col.find_one({"paper_id": paper_id})
    if not current:
        raise HTTPException(status_code=404, detail="paper not found")
    papers_col.update_one(
        {"paper_id": paper_id},
        {
            "$set": {
                "status": "published",
                "workflow_status": "published",
                "updated_at": datetime.utcnow(),
                "updated_by": admin.get("username"),
            }
        },
    )
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="publish",
        resource="paper",
        resource_id=str(paper_id),
    )
    return {"msg": "published", "paper_id": paper_id}


@router.post("/{paper_id}/offline")
def offline_paper(paper_id: int, admin=Depends(require_permission("paper:offline"))):
    _ensure_papers_collection()
    current = papers_col.find_one({"paper_id": paper_id})
    if not current:
        raise HTTPException(status_code=404, detail="paper not found")
    papers_col.update_one(
        {"paper_id": paper_id},
        {"$set": {"status": "offline", "updated_at": datetime.utcnow(), "updated_by": admin.get("username")}},
    )
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="offline",
        resource="paper",
        resource_id=str(paper_id),
    )
    return {"msg": "offline", "paper_id": paper_id}
