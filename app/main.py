from fastapi import FastAPI, Response
from fastapi.responses import FileResponse

from pydantic import BaseModel
from typing import Optional

from app.wrapper import (
    chat as wrapper_chat,
    delete_chain,
)
import app.error_codes as ec

app = FastAPI()


class ChatInput(BaseModel):
    conversation_id: str
    human_input: str


class ChatOutput(BaseModel):
    message: Optional[str] = None
    results: Optional[list] = None
    error_code: Optional[str] = None
    instructions: list = []
    instructions_str: str = ""
    tokens: Optional[int] = None
    price: Optional[float] = None


@app.post('/chat', response_model=ChatOutput, response_model_exclude_unset=True)
async def chat(input: ChatInput, response: Response):
    conversation_id = input.conversation_id
    human_input = input.human_input

    # Ensure text not too long
    if len(human_input) > 1000:
        response.status_code = 500  # Internal server error
        return ChatOutput(error_code=ec.ERR_INPUT_TOO_LONG)

    # Main call to generate results
    conversation_result = wrapper_chat(conversation_id, human_input)

    return conversation_result

################################################################


class ResetInput(BaseModel):
    conversation_id: str


@app.post('/reset')
async def reset(input: ResetInput):
    conversation_id = input.conversation_id

    delete_chain(conversation_id)

    return {'ok': True}

################################################################


@app.get('/')
async def index():
    return FileResponse('../html/index.html')


@app.get('/index.css')
async def index_css():
    return FileResponse('../html/index.css')


@app.get('/index.js')
async def index_js():
    return FileResponse('../html/index.js')
