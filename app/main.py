"""
This module creates the FastAPI application that constitutes the entry point of the chatbot.
It defines the input and output models and creates the endpoints.
"""

from contextlib import asynccontextmanager
from typing import Optional

from pydantic import BaseModel

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse

from app.agent import init_agent, send_message, clear_conversation
import app.error_codes as ec


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This function has three parts:
      * Before startup: Logic executed right before starting the API. Here we initialise the agent chain.
      * Yield: This is the standard way of passing the execution to the FastAPI app, so it can normally boot and serve requests.
      * After shutdown: Logic executed right after shutting down the API. Here we might want to free some memory, do some cleanup, etc.
    """

    ################################################################
    # Before startup                                               #
    ################################################################
    init_agent()

    ################################################################
    # Yield execution to API                                       #
    ################################################################
    yield

    ################################################################
    # After shutdown                                               #
    ################################################################
    pass


app = FastAPI(
    title="EPFL Graph Chatbot",
    description="API that serves the EPFL Graph chatbot",
    version="1.0.0",
    lifespan=lifespan
)


class ChatInput(BaseModel):
    conversation_id: str
    human_input: str


class ChatOutput(BaseModel):
    message: Optional[str] = None
    tool_interactions: Optional[list] = None
    error_code: Optional[str] = None
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
    prompt = input.human_input

    # Ensure text not too long
    if len(prompt) > 1000:
        response.status_code = 500  # Internal server error
        return ChatOutput(error_code=ec.ERR_INPUT_TOO_LONG)

    # Main call to generate results
    output = send_message(conversation_id, prompt)

    return output

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

    return {
        'ok': clear_conversation(input.conversation_id)
    }

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
