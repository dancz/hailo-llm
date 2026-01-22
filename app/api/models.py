from pydantic import BaseModel, Field
from typing import Optional, List, Union

class GenerateRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = True
    options: Optional[dict] = None

class GenerateResponse(BaseModel):
    model: str
    created_at: str
    response: str
    done: bool

class ChatMessage(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = True
    options: Optional[dict] = None

class ChatResponse(BaseModel):
    model: str
    created_at: str
    message: ChatMessage
    done: bool
