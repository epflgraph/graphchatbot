"""
This module creates the FastAPI application that constitutes the entry point of the chatbot.
It defines the input and output models and creates the endpoints.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends

from app.auth import get_user
from app.routers import secure, public

from app.agent import init_agent
from app.bots import registry as bot_registry


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
    bot_registry.init_bots()

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

app.include_router(
    public.router,
)
app.include_router(
    secure.router,
    dependencies=[Depends(get_user)]
)

if __name__ == "__main__":
    uvicorn.run(app)
