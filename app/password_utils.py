BCRYPT_MAX_PASSWORD_BYTES = 72


def truncate_bcrypt_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) <= BCRYPT_MAX_PASSWORD_BYTES:
        return password
    return password_bytes[:BCRYPT_MAX_PASSWORD_BYTES].decode("utf-8", errors="ignore")
