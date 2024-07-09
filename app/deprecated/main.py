"""
This module creates the FastAPI application that constitutes the entry point of the chatbot.
It defines the input and output models and creates the endpoints.
"""

from typing import Optional

from pydantic import BaseModel

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse

from app.deprecated.wrapper import (
    chat as old_wrapper_chat,
    delete_chain,
)
import app.error_codes as ec


app = FastAPI(
    title="EPFL Graph Chatbot",
    description="API that serves the EPFL Graph chatbot",
    version="0.1.0",
)


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
    """
    Sends a new message to the chatbot in the context of a given conversation. This is the main endpoint to interact with the chatbot.

    Args:
        input (ChatInput): Input object containing the conversation_id and the new piece of human_input. This is the payload of the request.
        response (Response): Actual response object provided by FastAPI. Do not provide this parameter, as it is handled automatically by FastAPI.

    Returns:
        ChatOutput: Output object containing either an error_code, if there was a problem, or a message and a results object, if everything was fine.
    """

    conversation_id = input.conversation_id
    human_input = input.human_input

    # Ensure text not too long
    if len(human_input) > 1000:
        response.status_code = 500  # Internal server error
        return ChatOutput(error_code=ec.ERR_INPUT_TOO_LONG)

    # Main call to generate results
    conversation_result = old_wrapper_chat(conversation_id, human_input)

    return conversation_result

################################################################


class ResetInput(BaseModel):
    conversation_id: str


@app.post('/reset')
async def reset(input: ResetInput):
    """
    Resets the conversation with a given conversation_id. The next message sent to that conversation will start a fresh interaction with the chatbot.

    Args:
        input (ChatInput): Input object containing the conversation_id to be reset.

    Returns:
        dict: Dictionary containing whether everything went well.
    """

    conversation_id = input.conversation_id

    delete_chain(conversation_id)

    return {'ok': True}

################################################################


@app.get('/')
async def index():
    """
    Serves the HTML file for the chatbot's frontend.
    """

    return FileResponse('../html/index.html')


@app.get('/index.css')
async def index_css():
    """
    Serves the CSS file for the chatbot's frontend.
    """

    return FileResponse('../html/index.css')


@app.get('/index.js')
async def index_js():
    """
    Serves the JS file for the chatbot's frontend.
    """

    return FileResponse('../html/index.js')
