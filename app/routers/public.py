import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from openai.types.chat.completion_create_params import CompletionCreateParams

from app.bots import registry as bot_registry
from app.bots.main import (
    agenerate_completion as bot_agenerate_completion,
    generate_completion as bot_generate_completion,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post('/chat/completions')
async def chat(chat_request: CompletionCreateParams):
    bot = bot_registry.get_bot(chat_request['model'])
    if bot is None:
        raise HTTPException(status_code=404, detail=f"Bot '{chat_request['model']}' not found")

    if chat_request.get('stream'):
        return StreamingResponse(
            bot_agenerate_completion(chat_request, bot),
            media_type="text/event-stream"
        )
    else:
        return await bot_generate_completion(chat_request, bot)


@router.get('/models')
async def models():
    return {
        "object": "list",
        "data": [
            {
                "id": bot.name,
                "object": "model",
                "created": 1686935002,
                "owned_by": "epfl-graph-cede",
            }
            for bot in bot_registry.list_bots()
        ],
    }