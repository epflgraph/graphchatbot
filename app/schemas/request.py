from __future__ import annotations  # Needed to evaluate all classes lazily, or else we need to keep track of their order. Follows https://peps.python.org/pep-0563/
from typing import List, Dict, Optional, Union, Literal
from pydantic import BaseModel

from app.schemas.audio import RequestAudio
from app.schemas.messages import RequestMessage
from app.schemas.prediction import RequestPrediction
from app.schemas.response_format import RequestResponseFormat
from app.schemas.stream_options import RequestStreamOptions
from app.schemas.tools import RequestTools, RequestToolChoice
from app.schemas.web_search_options import RequestWebSearchOptions

################################################################
# Request model                                                #
################################################################


class ChatRequest(BaseModel):
    messages: List[RequestMessage]
    model: str
    audio: Optional[RequestAudio] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, int]] = None
    logprobs: Optional[bool] = False
    max_completion_tokens: Optional[int] = None
    metadata: Optional[Dict[str, str]] = None
    modalities: Optional[List[Literal['text', 'audio']]] = ['text']
    n: Optional[int] = None
    parallel_tool_calls: Optional[bool] = True
    prediction: Optional[RequestPrediction] = None
    presence_penalty: Optional[float] = 0
    reasoning_effort: Optional[Literal['default', 'low', 'medium', 'high']] = 'medium'
    response_format: Optional[RequestResponseFormat] = None
    seed: Optional[int] = None
    service_tier: Optional[Literal['auto', 'default', 'flex']] = 'auto'
    stop: Optional[Union[str, list[str]]] = None
    store: Optional[bool] = False
    stream: Optional[bool] = False
    stream_options: Optional[RequestStreamOptions] = None
    temperature: Optional[float] = 1
    tool_choice: Optional[Union[Literal['none', 'auto', 'required'], RequestToolChoice]] = None
    tools: Optional[RequestTools] = None
    top_logprobs: Optional[int] = None
    top_p: Optional[float] = 1
    user: Optional[str] = None
    web_search_options: Optional[RequestWebSearchOptions] = None

    class Config:
        json_schema_extra = {'required': ['messages', 'model']}
