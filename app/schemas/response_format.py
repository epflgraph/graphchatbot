from __future__ import annotations  # Needed to evaluate all classes lazily, or else we need to keep track of their order. Follows https://peps.python.org/pep-0563/
from typing import Optional, Union, Literal
from pydantic import BaseModel, Field


class RequestTextResponseFormat(BaseModel):
    type: Literal['text']


class RequestJsonSchemaResponseFormat(BaseModel):
    type: Literal['json_schema']
    json_schema: RequestJsonSchemaResponseFormatJsonSchema


class RequestJsonSchemaResponseFormatJsonSchema(BaseModel):
    name: str
    description: Optional[str] = None
    my_schema: Optional[dict] = Field(None, alias='schema')
    strict: Optional[bool] = False


class RequestJsonObjectResponseFormat(BaseModel):
    type: Literal['json_object']


RequestResponseFormat = Union[
    RequestTextResponseFormat,
    RequestJsonSchemaResponseFormat,
    RequestJsonObjectResponseFormat,
]
