from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import require_permission
from app.services.audit import audit_log

try:
    from backend import db, users_col
except Exception:  # pragma: no cover
    db = None
    users_col = None


router = APIRouter()

DEFAULT_ROLES = [
    {"code": "user", "name": "普通用户", "description": "基础使用权限"},
    {"code": "editor", "name": "编辑", "description": "可维护论文内容"},
    {"code": "admin", "name": "管理员", "description": "完整管理权限"},
]

DEFAULT_PERMISSIONS = [
    {"code": "paper:view", "name": "查看论文"},
    {"code": "paper:create", "name": "创建论文"},
    {"code": "paper:update", "name": "编辑论文"},
    {"code": "paper:publish", "name": "发布论文"},
    {"code": "paper:offline", "name": "下架论文"},
    {"code": "user:view", "name": "查看用户"},
    {"code": "user:grant_role", "name": "分配角色"},
    {"code": "perm:grant", "name": "分配权限"},
    {"code": "job:view", "name": "查看任务"},
    {"code": "job:create", "name": "创建任务"},
    {"code": "job:retry", "name": "重试任务"},
    {"code": "review:view", "name": "查看审稿流程"},
    {"code": "review:manage", "name": "推进审稿流程"},
]


class UserRoleUpdate(BaseModel):
    role_codes: list[str] = Field(default_factory=list)


class RolePermissionUpdate(BaseModel):
    permissions: list[str] = Field(default_factory=list)


def _roles_col():
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB is not available")
    return db["roles"]


def _permissions_col():
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB is not available")
    return db["permissions"]


def _role_permissions_col():
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB is not available")
    return db["role_permissions"]


def _ensure_db():
    if users_col is None or db is None:
        raise HTTPException(status_code=500, detail="MongoDB is not available")


def _ensure_roles_and_permissions_seeded():
    for role in DEFAULT_ROLES:
        _roles_col().update_one({"code": role["code"]}, {"$set": role}, upsert=True)
    for perm in DEFAULT_PERMISSIONS:
        _permissions_col().update_one({"code": perm["code"]}, {"$set": perm}, upsert=True)

    full = [p["code"] for p in DEFAULT_PERMISSIONS]
    editor = [p for p in full if p not in {"user:grant_role", "perm:grant"}]
    basic = ["paper:view", "job:view"]
    defaults = {"admin": full, "editor": editor, "user": basic}
    for role_code, perms in defaults.items():
        _role_permissions_col().update_one(
            {"role_code": role_code},
            {"$setOnInsert": {"role_code": role_code, "permissions": perms}},
            upsert=True,
        )
        _role_permissions_col().update_one(
            {"role_code": role_code},
            {"$addToSet": {"permissions": {"$each": perms}}},
        )


@router.get("/roles")
def list_roles(_admin=Depends(require_permission("user:view"))):
    _ensure_db()
    _ensure_roles_and_permissions_seeded()
    rows = list(_roles_col().find({}, {"_id": 0}).sort("code", 1))
    return {"items": rows}


@router.get("/permissions")
def list_permissions(_admin=Depends(require_permission("perm:grant"))):
    _ensure_db()
    _ensure_roles_and_permissions_seeded()
    rows = list(_permissions_col().find({}, {"_id": 0}).sort("code", 1))
    return {"items": rows}


@router.get("/role-permissions")
def list_role_permissions(_admin=Depends(require_permission("perm:grant"))):
    _ensure_db()
    _ensure_roles_and_permissions_seeded()
    rows = list(_role_permissions_col().find({}, {"_id": 0}).sort("role_code", 1))
    return {"items": rows}


@router.put("/role-permissions/{role_code}")
def update_role_permissions(role_code: str, payload: RolePermissionUpdate, admin=Depends(require_permission("perm:grant"))):
    _ensure_db()
    _ensure_roles_and_permissions_seeded()

    role = _roles_col().find_one({"code": role_code})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    valid_codes = {r["code"] for r in _permissions_col().find({}, {"code": 1, "_id": 0})}
    bad = [c for c in payload.permissions if c not in valid_codes]
    if bad:
        raise HTTPException(status_code=400, detail=f"Unknown permissions: {', '.join(bad)}")

    _role_permissions_col().update_one(
        {"role_code": role_code},
        {
            "$set": {
                "role_code": role_code,
                "permissions": payload.permissions,
                "updated_at": datetime.utcnow(),
                "updated_by": admin.get("username"),
            }
        },
        upsert=True,
    )
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="update_permissions",
        resource="role",
        resource_id=role_code,
        detail={"permissions": payload.permissions},
    )
    return {"msg": "updated", "role_code": role_code, "permissions": payload.permissions}


@router.get("/users")
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    _admin=Depends(require_permission("user:view")),
):
    _ensure_db()
    query = {}
    if keyword:
        query["username"] = {"$regex": keyword, "$options": "i"}
    total = users_col.count_documents(query)
    cursor = (
        users_col.find(query, {"password_hash": 0})
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for d in cursor:
        items.append(
            {
                "username": d.get("username"),
                "role_codes": d.get("role_codes") or ["user"],
                "created_at": d.get("created_at"),
                "updated_at": d.get("updated_at"),
            }
        )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.put("/users/{username}/roles")
def update_user_roles(username: str, payload: UserRoleUpdate, admin=Depends(require_permission("user:grant_role"))):
    _ensure_db()
    _ensure_roles_and_permissions_seeded()
    valid_codes = {r["code"] for r in _roles_col().find({}, {"code": 1, "_id": 0})}
    bad = [c for c in payload.role_codes if c not in valid_codes]
    if bad:
        raise HTTPException(status_code=400, detail=f"Unknown role codes: {', '.join(bad)}")

    target = users_col.find_one({"username": username})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    role_codes = payload.role_codes or ["user"]
    users_col.update_one(
        {"username": username},
        {
            "$set": {
                "role_codes": role_codes,
                "updated_at": datetime.utcnow(),
                "updated_by": admin.get("username"),
            }
        },
    )
    audit_log(
        db,
        actor=admin.get("username", "unknown"),
        action="update_roles",
        resource="user",
        resource_id=username,
        detail={"role_codes": role_codes},
    )
    return {"msg": "updated", "username": username, "role_codes": role_codes}
