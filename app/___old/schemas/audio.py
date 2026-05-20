from __future__ import annotations  # Needed to evaluate all classes lazily, or else we need to keep track of their order. Follows https://peps.python.org/pep-0563/
from typing import Literal
from pydantic import BaseModel


class RequestAudio(BaseModel):
    format: Literal['wav', 'mp3', 'flac', 'opus', 'pcm16']
    voice: Literal['alloy', 'ash', 'ballad', 'coral', 'echo', 'fable', 'nova', 'onyx', 'sage', 'shimmer']
