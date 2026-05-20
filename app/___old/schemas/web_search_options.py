from __future__ import annotations  # Needed to evaluate all classes lazily, or else we need to keep track of their order. Follows https://peps.python.org/pep-0563/
from typing import Optional, Literal
from pydantic import BaseModel


class RequestWebSearchOptions(BaseModel):
    search_context_size: Optional[Literal['low', 'medium', 'high']] = 'medium'
    user_location: Optional[RequestWebSearchUserLocation] = None


class RequestWebSearchUserLocation(BaseModel):
    type: Literal['approximate']
    approximate: RequestWebSearchUserLocationParameters


class RequestWebSearchUserLocationParameters(BaseModel):
    city: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    timezone: Optional[str] = None
