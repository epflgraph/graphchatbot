from __future__ import annotations  # Needed to evaluate all classes lazily, or else we need to keep track of their order. Follows https://peps.python.org/pep-0563/
from typing import List, Union, Literal
from pydantic import BaseModel


class RequestPrediction(BaseModel):
    type: Literal['content']
    content: Union[str, List[RequestPredictionContent]]


class RequestPredictionContent(BaseModel):
    type: Literal['text']
    text: str
