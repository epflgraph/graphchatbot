import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.auth import get_user, get_admin, get_api_key, generate_api_key, insert_api_keys
from app.schemas import ChatRequest
from app.integrations import IntegrationConfig

from app.agent import generate_completion, agenerate_completion

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post('/chat/completions')
async def chat(chat_request: ChatRequest, user: Annotated[dict, Depends(get_user)]):
    """
    Creates a model response for the given chat conversation.

    Args:
        chat_request (ChatRequest): Input object containing the payload of the request.
        user (dict): Object containing the user information associated with the api_key in the header

    Returns:
        ChatResponse: Output object containing a chat completion based on the provided input.
    """

    # Check if user has access to the integration in the request
    integration = IntegrationConfig.from_name(chat_request.model)   # defaults to 'graph-chat'
    if integration.groups and len(set(integration.groups) & set(user['groups'])) == 0:
        logger.warning(f"User {user} doesn't have access to integration {chat_request.model}")
        raise HTTPException(status_code=403, detail="Missing or invalid API key")

    if chat_request.stream:
        return StreamingResponse(
            agenerate_completion(chat_request.model_dump()),
            media_type="text/event-stream"
        )
    else:
        return await generate_completion(chat_request.model_dump())


@router.get('/models')
async def models(user: Annotated[dict, Depends(get_user)]):
    # Compute list of allowed integrations for the current user based on their EPFL groups
    all_integration_names = IntegrationConfig.list_integrations()

    model_names = []
    for integration_name in all_integration_names:
        integration = IntegrationConfig.from_name(integration_name)

        if integration.groups is None or len(set(integration.groups) & set(user['groups'])) > 0:
            model_names.append(integration_name)

    return {
        "object": "list",
        "data": [
            {
                "id": model_name,
                "object": "model",
                "created": 1686935002,
                "owned_by": "epfl-graph-cede"
            }
            for model_name in model_names
        ],
    }


@router.get('/users')
async def users(sciper: str, email: str, admin: Annotated[dict, Depends(get_admin)]):
    logger.info(f"Accepted request for api key for sciper={sciper} and email={email}")

    # Fetch api key if it exists
    api_key = get_api_key(sciper, email)

    # Create new one if it doesn't exist
    if not api_key:
        api_key = generate_api_key()

        insert_api_keys([{
            'api_key': api_key,
            'sciper': sciper,
            'email': email,
        }])

    # Return user with api_key
    return {
        'sciper': sciper,
        'email': email,
        'api_key': api_key,
    }
