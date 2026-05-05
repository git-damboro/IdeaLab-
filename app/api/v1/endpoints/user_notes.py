from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

try:
    from backend import db
except Exception:  # pragma: no cover
    db = None


router = APIRouter()


class NoteUpsertRequest(BaseModel):
    user_id: str = Field(min_length=1)
    paper_id: int
    content: str = ""
    paper_title: str = ""
    paper_url: str = ""


def _notes_col():
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB is not available")
    return db["notes"]


def _papers_col():
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB is not available")
    return db["papers"]


@router.get("")
def get_note(user_id: str = Query(...), paper_id: int = Query(...)):
    col = _notes_col()
    doc = col.find_one({"user_id": user_id, "paper_id": paper_id})
    if not doc:
        return {"user_id": user_id, "paper_id": paper_id, "content": "", "updated_at": None}
    return {
        "user_id": doc.get("user_id"),
        "paper_id": doc.get("paper_id"),
        "content": doc.get("content", ""),
        "updated_at": doc.get("updated_at"),
    }


@router.post("")
def upsert_note(payload: NoteUpsertRequest):
    col = _notes_col()
    now = datetime.utcnow()
    set_doc = {
        "content": payload.content,
        "updated_at": now,
    }
    if payload.paper_title:
        set_doc["paper_title"] = payload.paper_title
    if payload.paper_url:
        set_doc["paper_url"] = payload.paper_url
    col.update_one(
        {"user_id": payload.user_id, "paper_id": payload.paper_id},
        {
            "$set": set_doc,
            "$setOnInsert": {
                "user_id": payload.user_id,
                "paper_id": payload.paper_id,
                "created_at": now,
            },
        },
        upsert=True,
    )
    return {"msg": "saved", "user_id": payload.user_id, "paper_id": payload.paper_id, "updated_at": now}


@router.get("/list")
def list_notes(
    user_id: str = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    keyword: str = Query(default=""),
):
    col = _notes_col()
    query = {"user_id": user_id}
    if keyword:
        query["content"] = {"$regex": keyword, "$options": "i"}

    total = col.count_documents(query)
    cursor = (
        col.find(query, {"_id": 0})
        .sort("updated_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(cursor)

    # Attach paper titles for note management UI.
    paper_ids = [x.get("paper_id") for x in items if x.get("paper_id") is not None]
    paper_meta_map = {}
    if paper_ids:
        str_ids = [str(pid) for pid in paper_ids]
        query = {"$or": [{"paper_id": {"$in": paper_ids}}, {"paper_id": {"$in": str_ids}}]}
        papers = _papers_col().find(query, {"paper_id": 1, "title": 1, "url": 1, "_id": 0})
        for p in papers:
            pid_raw = p.get("paper_id")
            if pid_raw is None:
                continue
            paper_meta_map[str(pid_raw)] = {"title": p.get("title", ""), "url": p.get("url", "")}

    result = []
    for n in items:
        result.append(
            {
                "user_id": n.get("user_id"),
                "paper_id": n.get("paper_id"),
                "content": n.get("content", ""),
                "created_at": n.get("created_at"),
                "updated_at": n.get("updated_at"),
                "paper_title": n.get("paper_title")
                or paper_meta_map.get(str(n.get("paper_id")), {}).get("title", ""),
                "paper_url": n.get("paper_url")
                or paper_meta_map.get(str(n.get("paper_id")), {}).get("url", ""),
            }
        )
    return {"items": result, "page": page, "page_size": page_size, "total": total}


@router.delete("")
def delete_note(user_id: str = Query(...), paper_id: int = Query(...)):
    col = _notes_col()
    result = col.delete_one({"user_id": user_id, "paper_id": paper_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"msg": "deleted", "user_id": user_id, "paper_id": paper_id}


@router.get("/export.md", response_class=PlainTextResponse)
def export_notes_markdown(user_id: str = Query(...)):
    col = _notes_col()
    cursor = col.find({"user_id": user_id}, {"_id": 0}).sort("updated_at", -1)
    items = list(cursor)
    lines = [f"# {user_id} 的笔记导出", ""]
    if not items:
        lines.append("（暂无笔记）")
        return "\n".join(lines)
    for idx, n in enumerate(items, start=1):
        title = n.get("paper_title") or f"Paper #{n.get('paper_id')}"
        lines.append(f"## {idx}. {title}")
        lines.append(f"- 论文ID: {n.get('paper_id')}")
        if n.get("paper_url"):
            lines.append(f"- 链接: {n.get('paper_url')}")
        if n.get("updated_at"):
            lines.append(f"- 更新时间: {n.get('updated_at')}")
        lines.append("")
        lines.append(n.get("content") or "（空笔记）")
        lines.append("")
    return "\n".join(lines)
