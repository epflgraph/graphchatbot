"""
This module creates the FastAPI application that constitutes the entry point of the chatbot.
It defines the input and output models and creates the endpoints.
"""

from contextlib import asynccontextmanager
from typing import Optional, Literal, Union

from pydantic import BaseModel

from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, FileResponse

from app.agent import init_agent, send_message, stream_send_message
import app.exercises as exercises
from app.errors import ERR_INPUT_TOO_LONG


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
    if len(prompt) > 5000:
        response.status_code = 500  # Internal server error
        return ChatOutput(error_code=ERR_INPUT_TOO_LONG)

    # Main call to generate results
    output = send_message(conversation_id, prompt)

    return output


@app.post('/stream_chat')
async def stream_chat(input: ChatInput):
    """
    Sends a new message to the chatbot in the context of a given conversation. This is the stream version of the main endpoint to interact with the chatbot.

    Args:
        input (ChatInput): Input object containing the conversation_id and the new piece of human_input. This is the payload of the request.

    Returns:
        StreamingResponse: Streams bits of the response asynchronously as they become available.
    """

    conversation_id = input.conversation_id
    prompt = input.human_input

    return StreamingResponse(stream_send_message(conversation_id, prompt), media_type='application/x-ndjson')


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


################################################################


class GenerateTextExerciseInput(BaseModel):
    text: str
    description: str
    bloom_level: Literal[None, 1, 2, 3, 4, 5, 6] = None
    include_solution: bool = True
    output_format: Literal['plain-text', 'markdown', 'latex'] = 'plain-text'
    llm_model: Literal['gpt-4o-mini', 'gpt-4o'] = 'gpt-4o-mini'


class GenerateLectureExerciseInput(BaseModel):
    lecture_id: str
    description: str
    bloom_level: Literal[None, 1, 2, 3, 4, 5, 6] = None
    include_solution: bool = True
    output_format: Literal['plain-text', 'markdown', 'latex'] = 'markdown'
    llm_model: Literal['gpt-4o-mini', 'gpt-4o'] = 'gpt-4o-mini'


@app.post('/generate_exercise')
async def generate_exercise(input: Union[GenerateTextExerciseInput, GenerateLectureExerciseInput]):
    """
    Generates an exercise about some given text or lecture.

    Args:
        input (Union[GenerateTextExerciseInput, GenerateLectureExerciseInput]): Input object containing text or lecture_id, a description and some other parameters like the bloom level or whether to include a solution.

    Returns:
        dict: An object containing the different field for the exercise.
    """

    description = input.description
    bloom_level = input.bloom_level
    include_solution = input.include_solution
    output_format = input.output_format
    llm_model = input.llm_model

    if isinstance(input, GenerateTextExerciseInput):
        return exercises.generate_text_exercise(input.text, description, bloom_level, include_solution, output_format, llm_model)
    elif isinstance(input, GenerateLectureExerciseInput):
        return exercises.generate_lecture_exercise(input.lecture_id, description, bloom_level, include_solution, output_format, llm_model)

    return {}
