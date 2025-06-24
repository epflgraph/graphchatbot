from __future__ import annotations  # Needed to evaluate all classes lazily, or else we need to keep track of their order. Follows https://peps.python.org/pep-0563/
from typing import Optional
from pydantic import BaseModel


class RequestStreamOptions(BaseModel):
    include_usage: Optional[bool] = None
