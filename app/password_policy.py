import re


PASSWORD_POLICY_ERROR_MESSAGES = {
    "length": "密码长度必须为6到16位",
    "charset": "密码只能包含字母和数字",
    "composition": "密码必须同时包含字母和数字",
}


def get_password_policy_error(password: str) -> str | None:
    if password is None:
        return PASSWORD_POLICY_ERROR_MESSAGES["length"]

    if len(password) < 6 or len(password) > 16:
        return PASSWORD_POLICY_ERROR_MESSAGES["length"]

    if not re.fullmatch(r"[A-Za-z0-9]+", password):
        return PASSWORD_POLICY_ERROR_MESSAGES["charset"]

    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return PASSWORD_POLICY_ERROR_MESSAGES["composition"]

    return None
