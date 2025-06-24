


################################################################
# Response models                                              #
################################################################


class MessageAnnotation(BaseModel):
    type: Literal['url_citation']
    url_citation: dict


class ResponseFunctionCall(BaseModel):
    name: str
    arguments: str


class ResponseAudio(BaseModel):
    id: str
    expires_at: int
    data: str
    transcript: str


class ResponseMessage(BaseModel):
    role: Literal['assistant']
    content: Optional[str] = None
    refusal: Optional[str] = None
    tool_calls: Optional[List[MessageToolCall]] = None
    annotations: Optional[List[MessageAnnotation]] = None
    function_call: Optional[ResponseFunctionCall] = None
    audio: Optional[ResponseAudio] = None


class TokenLogprob(BaseModel):
    token: str
    logprob: float
    bytes: List[int]
    top_logprobs: Optional[List[TokenLogprob]] = None


class ResponseChoice(BaseModel):
    index: int
    message: ResponseMessage
    logprobs: Optional[TokenLogprob] = None
    finish_reason: str


class CompletionTokenDetails(BaseModel):
    cached_tokens: Optional[int] = None
    audio_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    accepted_prediction_tokens: Optional[int] = None
    rejected_prediction_tokens: Optional[int] = None


class CompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: Optional[CompletionTokenDetails] = None
    completion_tokens_details: Optional[CompletionTokenDetails] = None


class CreateResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[ResponseChoice]
    usage: CompletionUsage
    service_tier: Optional[str] = None
