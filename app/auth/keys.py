import secrets


def generate_api_key(prefix="sk", length=48):
    token = secrets.token_urlsafe(length)[:length]
    return f"{prefix}-{token}"
