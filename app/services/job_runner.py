import csv
import json
import os
import threading
import time
from datetime import datetime

import bibtexparser
from bibtexparser.customization import convert_to_unicode
from pymongo import ReturnDocument


class JobRunner:
    """Simple in-process worker for ingest_jobs."""

    def __init__(self, db, poll_interval: float = 2.0):
        self.db = db
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread = None

    @property
    def jobs_col(self):
        return self.db["ingest_jobs"]

    @property
    def papers_col(self):
        return self.db["papers"]

    def _append_log(self, job_id, message: str):
        now = datetime.utcnow().isoformat()
        line = f"{now} | {message}"
        try:
            self.jobs_col.update_one({"_id": job_id}, {"$push": {"logs": {"$each": [line], "$slice": -500}}})
        except Exception:
            pass

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="ingest-job-runner")
        self._thread.start()
        print("INFO: ingest job runner started")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                job = self.jobs_col.find_one_and_update(
                    {"status": "queued"},
                    {
                        "$set": {
                            "status": "running",
                            "progress": 1,
                            "updated_at": datetime.utcnow(),
                            "started_at": datetime.utcnow(),
                        }
                    },
                    sort=[("created_at", 1)],
                    return_document=ReturnDocument.AFTER,
                )
                if not job:
                    time.sleep(self.poll_interval)
                    continue
                self._execute_job(job)
            except Exception as e:
                print(f"WARN: job runner loop error: {e}")
                time.sleep(self.poll_interval)

    def _execute_job(self, job: dict):
        job_id = job["_id"]
        self._append_log(job_id, f"开始执行任务 type={job.get('type')}")
        try:
            if job.get("type") == "import":
                inserted, total = self._run_import(job)
                self.jobs_col.update_one(
                    {"_id": job_id},
                    {
                        "$set": {
                            "status": "success",
                            "progress": 100,
                            "result": {"inserted": inserted, "total": total},
                            "updated_at": datetime.utcnow(),
                            "finished_at": datetime.utcnow(),
                        }
                    },
                )
                self._append_log(job_id, f"导入完成：新增 {inserted}/{total}")
            elif job.get("type") in {"reindex", "summary"}:
                time.sleep(1)
                self.jobs_col.update_one(
                    {"_id": job_id},
                    {
                        "$set": {
                            "status": "success",
                            "progress": 100,
                            "updated_at": datetime.utcnow(),
                            "finished_at": datetime.utcnow(),
                        }
                    },
                )
                self._append_log(job_id, f"任务执行完成 type={job.get('type')}")
            else:
                raise ValueError(f"Unsupported job type: {job.get('type')}")
        except Exception as e:
            self.jobs_col.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(e),
                        "updated_at": datetime.utcnow(),
                        "finished_at": datetime.utcnow(),
                    }
                },
            )
            self._append_log(job_id, f"任务失败: {e}")

    def _run_import(self, job: dict) -> tuple[int, int]:
        payload = job.get("payload") or {}
        source = payload.get("source") or "data/anthology+abstracts1.bib"
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        source_path = source if os.path.isabs(source) else os.path.join(root_dir, source)
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Import source not found: {source_path}")
        self._append_log(job["_id"], f"读取数据源 {source}")

        ext = os.path.splitext(source_path)[1].lower()
        if ext == ".bib":
            entries = self._load_bib_entries(source_path)
        elif ext == ".json":
            entries = self._load_json_entries(source_path)
        elif ext == ".csv":
            entries = self._load_csv_entries(source_path)
        else:
            raise ValueError(f"Unsupported import file type: {ext}")

        total = len(entries)
        if total == 0:
            self._append_log(job["_id"], "导入数据为空")
            return 0, 0

        inserted = 0
        for idx, entry in enumerate(entries, start=1):
            paper_id = self._stable_paper_id(entry, idx)
            doc = {
                "paper_id": paper_id,
                "title": self._clean(entry.get("title")),
                "abstract": self._clean(entry.get("abstract")),
                "authors": self._parse_authors(entry.get("author")),
                "year_int": self._parse_year(entry.get("year")),
                "month": self._clean(entry.get("month")),
                "booktitle": self._clean(entry.get("booktitle") or entry.get("journal") or entry.get("venue")),
                "url": self._clean(entry.get("url")),
                "status": "published",
                "updated_at": datetime.utcnow(),
            }
            result = self.papers_col.update_one({"paper_id": paper_id}, {"$setOnInsert": doc}, upsert=True)
            if result.upserted_id is not None:
                inserted += 1

            if idx % 50 == 0 or idx == total:
                progress = max(1, int(idx / total * 100))
                self.jobs_col.update_one(
                    {"_id": job["_id"]},
                    {"$set": {"progress": progress, "updated_at": datetime.utcnow()}},
                )
                if idx % 500 == 0 or idx == total:
                    self._append_log(job["_id"], f"导入进度: {idx}/{total}")

        return inserted, total

    def _load_bib_entries(self, source_path: str) -> list[dict]:
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        parser.customization = convert_to_unicode
        with open(source_path, "r", encoding="utf-8") as f:
            return bibtexparser.load(f, parser=parser).entries

    def _load_json_entries(self, source_path: str) -> list[dict]:
        with open(source_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            payload = payload.get("items") or payload.get("papers") or []
        if not isinstance(payload, list):
            raise ValueError("JSON import format must be an array or object with items/papers field")
        return [self._normalize_record(x) for x in payload]

    def _load_csv_entries(self, source_path: str) -> list[dict]:
        with open(source_path, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        return [self._normalize_record(x) for x in rows]

    @staticmethod
    def _normalize_record(record: dict) -> dict:
        title = record.get("title") or record.get("Title") or ""
        abstract = record.get("abstract") or record.get("summary") or record.get("Abstract") or ""
        authors = record.get("author") or record.get("authors") or record.get("Author") or ""
        year = record.get("year") or record.get("Year") or ""
        venue = record.get("booktitle") or record.get("journal") or record.get("venue") or ""
        return {
            "ID": record.get("ID") or record.get("paper_id") or "",
            "title": title,
            "abstract": abstract,
            "author": authors,
            "year": year,
            "booktitle": venue,
            "url": record.get("url") or "",
            "month": record.get("month") or "",
        }

    @staticmethod
    def _clean(value):
        if not value:
            return ""
        return str(value).replace("{", "").replace("}", "").strip()

    @staticmethod
    def _parse_year(year):
        if not year:
            return 0
        s = str(year)
        digits = "".join(ch for ch in s if ch.isdigit())
        if len(digits) >= 4:
            return int(digits[:4])
        return 0

    @staticmethod
    def _parse_authors(raw):
        if not raw:
            return []
        text = str(raw).replace("\n", " ")
        if ";" in text and " and " not in text:
            return [a.strip() for a in text.split(";") if a.strip()]
        return [a.strip() for a in text.split(" and ") if a.strip()]

    @staticmethod
    def _stable_paper_id(entry, idx: int = 0):
        key = (entry.get("ID") or "").strip()
        title = (entry.get("title") or "").strip()
        year = (entry.get("year") or "").strip()
        basis = f"{key}|{title}|{year}|{idx}"
        return abs(hash(basis)) % 10_000_000_000
