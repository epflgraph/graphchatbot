from fastapi import FastAPI, Response
from fastapi.responses import FileResponse

from pydantic import BaseModel
from typing import Optional

from app.conversation import conversation, wrap_nlp
# from app.conversation_tools import conversation


app = FastAPI()


class ChatInput(BaseModel):
    conversation_id: str
    text: str
    return_nlp: Optional[bool] = False


@app.post('/chat')
async def chat(input: ChatInput, response: Response):
    conversation_id = input.conversation_id
    text = input.text
    return_nlp = input.return_nlp

    # Ensure text not too long
    if len(text) > 1000:
        response.status_code = 413  # Content too large
        return []

    # Main call to generate results
    results, error = conversation(conversation_id, text)

    if error:
        response.status_code = 500  # Internal server error
        return []

    # Limit nodeset length
    for i in range(len(results)):
        results[i]['nodeset'] = results[i]['nodeset'][:10]

    # Wrap results in natural language
    if return_nlp:
        output_text = wrap_nlp(conversation_id, text, results)
        return {'text': output_text}

    return results


@app.get('/')
async def index():
    return FileResponse('../html/index.html')


@app.get('/index.css')
async def index_css():
    return FileResponse('../html/index.css')


@app.get('/index.js')
async def index_js():
    return FileResponse('../html/index.js')
