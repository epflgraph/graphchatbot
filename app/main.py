from fastapi import FastAPI, Response
from fastapi.responses import FileResponse

from pydantic import BaseModel
from typing import Optional

from app.conversation import conversation, wrap_nlp
# from app.conversation_tools import conversation
import app.error_codes as ec

app = FastAPI()


class ChatInput(BaseModel):
    conversation_id: str
    text: str
    return_nlp: Optional[bool] = False


class ChatOutput(BaseModel):
    results: Optional[list] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    tokens: Optional[int] = None
    price: Optional[float] = None


@app.post('/chat', response_model=ChatOutput, response_model_exclude_unset=True)
async def chat(input: ChatInput, response: Response):
    conversation_id = input.conversation_id
    text = input.text
    return_nlp = input.return_nlp

    # Ensure text not too long
    if len(text) > 1000:
        response.status_code = 500
        return ChatOutput(error_code=ec.ERR_INPUT_TOO_LONG)

    # Main call to generate results
    conversation_result = conversation(conversation_id, text)

    # Prepare output object with extra fields
    output = ChatOutput()
    for key in ['tokens', 'price']:
        if key in conversation_result:
            setattr(output, key, conversation_result[key])

    # If there was an error, return status code 500 and the error info
    if 'error_code' in conversation_result:
        response.status_code = 500  # Internal server error
        output.error_code = conversation_result['error_code']

        if 'message' in conversation_result:
            output.message = conversation_result['message']

        return output

    # --- If we reach this point, the conversation succeeded and "results" must be set ---

    # Limit nodeset length
    for i in range(len(conversation_result['results'])):
        conversation_result['results'][i]['nodeset'] = conversation_result['results'][i]['nodeset'][:10]

    # Set results on output object
    output.results = conversation_result['results']

    # Wrap results in natural language if needed
    if return_nlp:
        output.message = wrap_nlp(conversation_id, text, conversation_result['results'])

    return output


@app.get('/')
async def index():
    return FileResponse('../html/index.html')


@app.get('/index.css')
async def index_css():
    return FileResponse('../html/index.css')


@app.get('/index.js')
async def index_js():
    return FileResponse('../html/index.js')
