import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from openai.types.chat.completion_create_params import CompletionCreateParams

from app.auth import get_user, get_admin, get_api_key, generate_api_key, insert_api_keys
from app.bots import registry as bot_registry
from app.bots.main import generate_completion as bot_generate_completion, agenerate_completion as bot_agenerate_completion

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post('/chat/completions')
async def chat(chat_request: CompletionCreateParams, user: Annotated[dict, Depends(get_user)]):
    bot = bot_registry.get_bot(chat_request['model'])
    if bot is None:
        raise HTTPException(status_code=404, detail=f"Bot '{chat_request['model']}' not found")

    if bot.groups and len(set(bot.groups) & set(user['groups'])) == 0:
        logger.warning(f"User {user} doesn't have access to bot {chat_request['model']}")
        raise HTTPException(status_code=403, detail="Missing or invalid API key")

    if chat_request.get('stream'):
        return StreamingResponse(
            bot_agenerate_completion(chat_request, bot),
            media_type="text/event-stream"
        )
    else:
        return await bot_generate_completion(chat_request, bot)


@router.get('/models')
async def models(user: Annotated[dict, Depends(get_user)]):
    user_groups = set(user['groups'])
    allowed_bots = []
    for bot in bot_registry.list_bots():
        shared_groups = set(bot.groups) & user_groups if bot.groups else set()
        if not bot.groups or shared_groups:
            allowed_bots.append(bot.name)

    return {
        "object": "list",
        "data": [
            {
                "id": name,
                "object": "model",
                "created": 1686935002,
                "owned_by": "epfl-graph-cede"
            }
            for name in allowed_bots
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
