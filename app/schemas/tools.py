from __future__ import annotations  # Needed to evaluate all classes lazily, or else we need to keep track of their order. Follows https://peps.python.org/pep-0563/
from typing import List, Optional, Literal
from pydantic import BaseModel


class RequestToolChoice(BaseModel):
    type: Literal['function']
    function: RequestToolChoiceFunction


class RequestToolChoiceFunction(BaseModel):
    name: str


class RequestTool(BaseModel):
    type: Literal['function']
    function: RequestToolFunction


class RequestToolFunction(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[dict] = None
    strict: Optional[bool] = False


RequestTools = List[RequestTool]
