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
