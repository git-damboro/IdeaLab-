from fastapi import APIRouter, HTTPException

try:
    from backend import db
except Exception:  # pragma: no cover
    db = None


router = APIRouter()


def _papers_col():
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB is not available")
    return db["papers"]


@router.get("/{paper_id}")
def get_paper(paper_id: int):
    col = _papers_col()
    doc = col.find_one({"$or": [{"paper_id": paper_id}, {"paper_id": str(paper_id)}]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {
        "paper_id": doc.get("paper_id"),
        "title": doc.get("title", ""),
        "abstract": doc.get("abstract", ""),
        "year": doc.get("year_int") or doc.get("year"),
        "month": doc.get("month", ""),
        "url": doc.get("url", ""),
        "authors": doc.get("authors", []),
        "venue": doc.get("booktitle") or doc.get("venue", ""),
    }

