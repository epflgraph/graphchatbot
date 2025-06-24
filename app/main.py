"""
This module creates the FastAPI application that constitutes the entry point of the chatbot.
It defines the input and output models and creates the endpoints.
"""

from contextlib import asynccontextmanager
from typing import Union

from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, FileResponse

from app.schemas import ChatRequest
from app.old_schemas import GenerateTextExerciseInput, GenerateLectureExerciseInput
from app.agent import init_agent, generate_completion, agenerate_completion
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


@app.post('/chat/completions')
async def chat(chat_request: ChatRequest):
    """
    Creates a model response for the given chat conversation.

    Args:
        chat_request (ChatRequest): Input object containing the payload of the request.

    Returns:
        ChatResponse: Output object containing a chat completion based on the provided input.
    """

    if chat_request.stream:
        return StreamingResponse(
            agenerate_completion(chat_request.dict()),
            media_type="application/x-ndjson"
        )
    else:
        return generate_completion(chat_request.dict())


@app.get('/models')
async def models():

    return {
      "object": "list",
      "data": [
        {
          "id": "chatbot",
          "object": "model",
          "created": 1686935002,
          "owned_by": "epfl-graph-cede"
        },
      ],
    }


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
