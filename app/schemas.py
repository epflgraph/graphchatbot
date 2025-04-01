from typing import Optional, Literal, Union

from pydantic import BaseModel


class ChatInput(BaseModel):
    conversation_id: str
    human_input: str
    integrations: Optional[list[str]] = None
    use_tools: Optional[bool] = True
    style: Optional[str] = None
    style_prompt: Optional[str] = None

    def to_dict(self):
        return {
            'conversation_id': self.conversation_id,
            'human_input': self.human_input,
            'integrations': self.integrations if self.integrations else [],
            'use_tools': self.use_tools,
            'style': self.style,
            'style_prompt': self.style_prompt,
        }


class ChatOutput(BaseModel):
    message: Optional[str] = None
    tool_interactions: Optional[list] = None
    error_code: Optional[str] = None
    tokens: Optional[int] = None
    price: Optional[float] = None


class GenerateTextExerciseInput(BaseModel):
    text: str
    description: str
    bloom_level: Literal[None, 1, 2, 3, 4, 5, 6] = None
    include_solution: bool = True
    output_format: Literal['plain-text', 'markdown', 'latex'] = 'plain-text'
    llm_model: Literal['gpt-4o-mini', 'gpt-4o'] = 'gpt-4o-mini'
    openai_api_key: str


class GenerateLectureExerciseInput(BaseModel):
    lecture_id: str
    description: str
    bloom_level: Literal[None, 1, 2, 3, 4, 5, 6] = None
    include_solution: bool = True
    output_format: Literal['plain-text', 'markdown', 'latex'] = 'markdown'
    llm_model: Literal['gpt-4o-mini', 'gpt-4o'] = 'gpt-4o-mini'
    openai_api_key: str
