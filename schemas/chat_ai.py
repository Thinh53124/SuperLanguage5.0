from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ConversationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    language_code: Literal["English", "Japanese"]

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Chủ đề hội thoại không được để trống.")
        return value


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    language_code: str
    created_at: Optional[datetime] = None

class MessageSend(BaseModel):
    conversation_id: UUID
    user_message: str = Field(min_length=1, max_length=4000)

    @field_validator("user_message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tin nhắn không được để trống.")
        return value

class MessageResponse(BaseModel):
    conversation_id: UUID
    user_message: str
    ai_response: str
    ai_feedback: Optional[str] = None


class AudioUploadResponse(BaseModel):
    conversation_id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    storage_path: str