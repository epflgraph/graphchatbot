from fastapi import FastAPI, Response
from fastapi.responses import FileResponse

from pydantic import BaseModel
from typing import Optional

from app.wrapper import chat as wrapper_chat
from app.conversation import conversation, wrap_nlp
# from app.conversation_tools import conversation
import app.error_codes as ec

app = FastAPI()


class ChatInput(BaseModel):
    conversation_id: str
    human_input: str
    return_nlp: Optional[bool] = True


class ChatOutput(BaseModel):
    results: Optional[list] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    formatted_message: Optional[str] = None
    formatting_dict: Optional[dict] = None
    tokens: Optional[int] = None
    price: Optional[float] = None


@app.post('/old_chat', response_model=ChatOutput, response_model_exclude_unset=True)
async def old_chat(input: ChatInput, response: Response):
    conversation_id = input.conversation_id
    human_input = input.human_input
    return_nlp = input.return_nlp

    # Ensure text not too long
    if len(human_input) > 1000:
        response.status_code = 500
        return ChatOutput(error_code=ec.ERR_INPUT_TOO_LONG)

    # Main call to generate results
    conversation_result = conversation(conversation_id, human_input)

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
        wrapping_nlp_result = wrap_nlp(conversation_id, human_input, conversation_result['results'])
        output.message = wrapping_nlp_result['message']
        output.formatted_message = wrapping_nlp_result['formatted_message']
        output.formatting_dict = wrapping_nlp_result['formatting_dict']

    return output


@app.post('/chat', response_model=ChatOutput, response_model_exclude_unset=True)
async def chat(input: ChatInput, response: Response):
    conversation_id = input.conversation_id
    human_input = input.human_input

    # Ensure text not too long
    if len(human_input) > 1000:
        response.status_code = 500  # Internal server error
        return ChatOutput(error_code=ec.ERR_INPUT_TOO_LONG)

    # Main call to generate results
    conversation_result = wrapper_chat(conversation_id, human_input)

    return conversation_result

################################################################


@app.get('/')
async def index():
    return FileResponse('../html/index.html')


@app.get('/index.css')
async def index_css():
    return FileResponse('../html/index.css')


@app.get('/index.js')
async def index_js():
    return FileResponse('../html/index.js')
