from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.groups import get_user_groups

import app.auth.db as db

http_bearer = HTTPBearer()


def get_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)]):
    api_key = credentials.credentials

    # Verify auth scheme
    if credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=403, detail="Invalid auth scheme")

    # Fetch user associated with api_key from database
    user = db.get_user(api_key)

    # Verify api_key
    if not user or not user['is_active']:
        print('[AUTH]', f"User not found for api key {api_key}")
        raise HTTPException(status_code=403, detail="Missing or invalid API key")

    # Fetch user groups
    user['groups'] = get_user_groups(user['sciper'])

    return user


def get_admin(user: Annotated[dict, Depends(get_user)]):
    if 'graph-chatbot-admins' not in user['groups']:
        raise HTTPException(status_code=403, detail="User is not admin")

    return user
