from starlette.responses import FileResponse

from fastapi import FastAPI

from pydantic import BaseModel

from app.conversation import conversation
# from app.conversation_tools import conversation


class Input(BaseModel):
    text: str


class Output(BaseModel):
    text: str
    context_message: str
    context_dict: dict


app = FastAPI()


@app.post('/chat')
async def chat(input: Input):
    text, context_message, context_dict = conversation(input.text)
    return Output(text=text, context_message=context_message, context_dict=context_dict)


@app.get('/')
async def index():
    return FileResponse('html/index.html')
