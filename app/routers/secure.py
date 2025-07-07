from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.auth import check_api_key
from app.schemas import ChatRequest

from app.integrations import IntegrationConfig

from app.agent import generate_completion, agenerate_completion


router = APIRouter()


@router.post('/chat/completions')
async def chat(chat_request: ChatRequest, user: Annotated[dict, Depends(check_api_key)]):
    """
    Creates a model response for the given chat conversation.

    Args:
        chat_request (ChatRequest): Input object containing the payload of the request.
        user (dict): Object containing the user information associated with the api_key in the header

    Returns:
        ChatResponse: Output object containing a chat completion based on the provided input.
    """

    if chat_request.model not in user['integrations'] and '*' not in user['integrations']:
        print('[AUTH]', f"User {user} doesn't have access to integration {chat_request.model}")
        raise HTTPException(status_code=403, detail="Missing or invalid API key")

    if chat_request.stream:
        return StreamingResponse(
            agenerate_completion(chat_request.dict()),
            media_type="application/x-ndjson"
        )
    else:
        return generate_completion(chat_request.dict())


@router.get('/models')
async def models(user: Annotated[dict, Depends(check_api_key)]):
    all_model_names = IntegrationConfig.list_integrations()

    if '*' in user['integrations']:
        model_names = all_model_names
    else:
        model_names = [model_name for model_name in all_model_names if model_name in user['integrations']]

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
