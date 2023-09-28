from starlette.responses import FileResponse

from fastapi import FastAPI

from pydantic import BaseModel

from app.conversation import conversation
# from app.conversation_tools import conversation


class Input(BaseModel):
    text: str


class Output(BaseModel):
    context: str
    text: str


app = FastAPI()


@app.post('/chat')
async def chat(input: Input):
    context, text = conversation(input.text)
    return Output(context=context, text=text)


@app.get('/')
async def index():
    return FileResponse('html/index.html')
