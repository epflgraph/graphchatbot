from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.db import get_user

http_bearer = HTTPBearer()


def check_api_key(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)):
    api_key = credentials.credentials

    # Verify auth scheme
    if credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=403, detail="Invalid auth scheme")

    # Fetch user associated with api_key from database
    user = get_user(api_key)

    # Verify api_key
    if not user or not user['is_active']:
        print('[AUTH]', f"User not found for api key {api_key}")
        raise HTTPException(status_code=403, detail="Missing or invalid API key")

    return user

