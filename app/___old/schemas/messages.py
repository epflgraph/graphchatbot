from __future__ import annotations  # Needed to evaluate all classes lazily, or else we need to keep track of their order. Follows https://peps.python.org/pep-0563/
from typing import List, Optional, Union, Literal
from pydantic import BaseModel


class RequestDeveloperMessage(BaseModel):
    role: Literal['developer']
    content: Union[str, List[RequestMessageContentPartText]]
    name: Optional[str] = None


class RequestSystemMessage(BaseModel):
    role: Literal['system']
    content: Union[str, List[RequestMessageContentPartText]]
    name: Optional[str] = None


class RequestUserMessage(BaseModel):
    role: Literal['user']
    content: Union[
        str,
        List[
            RequestMessageContentPartText |
            RequestMessageContentPartImage |
            RequestMessageContentPartAudio |
            RequestMessageContentPartFile
        ]
    ]
    name: Optional[str] = None


class RequestAssistantMessage(BaseModel):
    role: Literal['assistant']
    content: Optional[
        Union[
            str,
            List[
                RequestMessageContentPartText |
                RequestMessageContentPartRefusal
                ]
        ]
    ] = None
    refusal: Optional[str] = None
    name: Optional[str] = None
    # audio: Optional[RequestAssistantMessageAudioReference] = None     # This seems to break even when it is None, perhaps a LangChain bug
    tool_calls: Optional[List[RequestAssistantMessageToolCall]] = None


class RequestToolMessage(BaseModel):
    role: Literal['tool']
    content: Union[str, List[RequestMessageContentPartText]]
    tool_call_id: str


class RequestFunctionMessage(BaseModel):
    role: Literal['function']
    name: str
    content: Optional[str] = None


RequestMessage = Union[
    RequestSystemMessage,
    RequestDeveloperMessage,
    RequestUserMessage,
    RequestAssistantMessage,
    RequestToolMessage,
    RequestFunctionMessage
]


class RequestMessageContentPartText(BaseModel):
    type: Literal['text']
    text: str


class RequestMessageContentPartImageUrl(BaseModel):
    url: str
    detail: Literal['auto', 'low', 'high'] = 'auto'


class RequestMessageContentPartImage(BaseModel):
    type: Literal['image_url']
    image_url: RequestMessageContentPartImageUrl


class RequestMessageContentPartAudioData(BaseModel):
    data: str
    format: Literal['wav', 'mp3']


class RequestMessageContentPartAudio(BaseModel):
    type: Literal['input_audio']
    input_audio: RequestMessageContentPartAudioData


class RequestMessageContentPartFileData(BaseModel):
    filename: Optional[str] = None
    file_data: Optional[str] = None
    file_id: Optional[str] = None


class RequestMessageContentPartFile(BaseModel):
    type: Literal['file']
    file: RequestMessageContentPartFileData


class RequestMessageContentPartRefusal(BaseModel):
    type: Literal['refusal']
    refusal: str


class RequestAssistantMessageAudioReference(BaseModel):
    id: str


class RequestAssistantMessageToolCall(BaseModel):
    id: str
    type: Literal['function']
    function: RequestAssistantMessageToolCallFunction


class RequestAssistantMessageToolCallFunction(BaseModel):
    name: str
    arguments: str
