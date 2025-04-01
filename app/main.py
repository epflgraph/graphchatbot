"""
This module creates the FastAPI application that constitutes the entry point of the chatbot.
It defines the input and output models and creates the endpoints.
"""

from contextlib import asynccontextmanager
from typing import Union

from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, FileResponse

from app.schemas import ChatInput, ChatOutput, GenerateTextExerciseInput, GenerateLectureExerciseInput
from app.agent import init_agent, send_message, stream_send_message
import app.exercises as exercises


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

    return send_message(input.to_dict())


@app.post('/stream_chat')
async def stream_chat(input: ChatInput):
    """
    Sends a new message to the chatbot in the context of a given conversation. This is the stream version of the main endpoint to interact with the chatbot.

    Args:
        input (ChatInput): Input object containing the conversation_id and the new piece of human_input. This is the payload of the request.

    Returns:
        StreamingResponse: Streams bits of the response asynchronously as they become available.
    """

    return StreamingResponse(stream_send_message(input.to_dict()), media_type='application/x-ndjson')


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
    openai_api_key = input.openai_api_key

    if isinstance(input, GenerateTextExerciseInput):
        return exercises.generate_text_exercise(input.text, description, bloom_level, include_solution, output_format, llm_model, openai_api_key)
    elif isinstance(input, GenerateLectureExerciseInput):
        return exercises.generate_lecture_exercise(input.lecture_id, description, bloom_level, include_solution, output_format, llm_model, openai_api_key)

    return {}
