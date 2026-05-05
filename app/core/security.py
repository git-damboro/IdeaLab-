import os
import sys

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

try:
    from backend import SECRET_KEY, ALGORITHM, users_col
except Exception:  # pragma: no cover - safe fallback if import order changes
    SECRET_KEY = "your_super_secret_key"
    ALGORITHM = "HS256"
    users_col = None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if users_col is None:
        # Fallback when DB is unavailable, still return basic principal from token.
        return {"username": username, "role_codes": ["user"]}

    user = users_col.find_one({"username": username})
    if not user:
        raise credentials_exception
    return user


def require_admin(user=Depends(get_current_user)):
    roles = user.get("role_codes") or []
    username = user.get("username")
    if "admin" in roles or username == "admin":
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


def user_permission_codes(user: dict) -> set[str]:
    roles = user.get("role_codes") or []
    username = user.get("username")
    if username == "admin":
        roles = list(set(roles + ["admin"]))

    if users_col is None:
        return set()

    # Lazy access via backend.db for minimal coupling.
    try:
        from backend import db
    except Exception:
        db = None
    if db is None:
        return set()

    mappings = db["role_permissions"].find({"role_code": {"$in": roles}}, {"permissions": 1, "_id": 0})
    result = set()
    for m in mappings:
        result.update(m.get("permissions") or [])
    return result


def require_permission(permission_code: str):
    def _checker(user=Depends(get_current_user)):
        perms = user_permission_codes(user)
        roles = user.get("role_codes") or []
        username = user.get("username")
        if username == "admin" or "admin" in roles or permission_code in perms:
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission required: {permission_code}")

    return _checker
