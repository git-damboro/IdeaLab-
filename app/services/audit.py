from datetime import datetime


def audit_log(db, actor: str, action: str, resource: str, resource_id: str, detail: dict | None = None):
    if db is None:
        return
    try:
        db["audit_logs"].insert_one(
            {
                "actor": actor,
                "action": action,
                "resource": resource,
                "resource_id": str(resource_id),
                "detail": detail or {},
                "created_at": datetime.utcnow(),
            }
        )
    except Exception as e:
        print(f"WARN: audit_log failed: {e}")

