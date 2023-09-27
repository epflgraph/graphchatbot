from starlette.responses import FileResponse

from fastapi import FastAPI

from pydantic import BaseModel

from app.conversation import conversation
# from app.conversation_tools import conversation


class Input(BaseModel):
    text: str


class Output(BaseModel):
    text: str


app = FastAPI()


@app.post('/chat')
async def chat(input: Input):
    return Output(text=conversation(input.text))


@app.get('/')
async def index():
    return FileResponse('index.html')
