try:
    from app.password_policy import get_password_policy_error
except ModuleNotFoundError:
    from password_policy import get_password_policy_error


def user_requires_password_change(user: dict) -> bool:
    return bool(user.get("must_change_password"))


def bootstrap_default_admin(
    users_col,
    *,
    admin_username: str,
    admin_password: str,
    hash_password,
    now,
) -> bool:
    if users_col is None or not admin_username or not admin_password:
        return False

    policy_error = get_password_policy_error(admin_password)
    if policy_error:
        return False

    if users_col.find_one({"role_codes": "admin"}):
        return False

    if users_col.find_one({"username": admin_username}):
        return False

    users_col.insert_one(
        {
            "username": admin_username,
            "password_hash": hash_password(admin_password),
            "role_codes": ["admin"],
            "status": "active",
            "must_change_password": True,
            "created_at": now(),
            "updated_at": now(),
        }
    )
    return True
