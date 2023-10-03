from fastapi import FastAPI, Response
from fastapi.responses import FileResponse

from pydantic import BaseModel

from app.conversation import conversation
# from app.conversation_tools import conversation


class ChatInput(BaseModel):
    conversation_id: str
    text: str


class ChatOutput(BaseModel):
    nodeset: list
    context: dict
    context_message: str


app = FastAPI()


@app.post('/chat')
async def chat(input: ChatInput, response: Response):
    conversation_id = input.conversation_id
    text = input.text

    # Ensure text not too long
    if len(text) > 1000:
        response.status_code = 413  # Content too large
        return ChatOutput(nodeset=[], context={}, context_message='')

    # Main call to generate result nodeset
    nodeset, context, context_message = conversation(conversation_id, text)

    # Limit nodeset length
    nodeset = nodeset[:10]

    if 'error' in context:
        response.status_code = 500  # Internal server error

    return ChatOutput(nodeset=nodeset, context=context, context_message=context_message)


@app.get('/')
async def index():
    return FileResponse('html/index.html')


@app.get('/index.css')
async def index_css():
    return FileResponse('html/index.css')


@app.get('/index.js')
async def index_js():
    return FileResponse('html/index.js')
