from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.profile import LANG_PATTERN, Level

PartOfSpeech = Literal["noun", "verb", "adjective", "adverb", "phrase", "other"]


class WordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language_code: str = Field(pattern=LANG_PATTERN)
    word: str = Field(min_length=1, max_length=150)
    meaning: str = Field(min_length=1, max_length=500)
    phonetic: Optional[str] = Field(default=None, max_length=100)
    part_of_speech: Optional[PartOfSpeech] = None
    audio_url: Optional[str] = Field(default=None, max_length=500)
    example_sentence: Optional[str] = Field(default=None, max_length=1000)
    example_meaning: Optional[str] = Field(default=None, max_length=1000)
    level: Level = "A1"
    topic_ids: list[int] = Field(min_length=1, max_length=20)

    @field_validator("part_of_speech", mode="before")
    @classmethod
    def clean_part_of_speech(cls, value: Any) -> Optional[str]:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        v = str(value).strip().lower()
        if v not in ("noun", "verb", "adjective", "adverb", "phrase", "other"):
            return "other"
        return v

    @field_validator("level", mode="before")
    @classmethod
    def clean_level(cls, value: Any) -> str:
        if not value:
            return "A1"
        v = str(value).strip().upper()
        if v not in ("A1", "A2", "B1", "B2", "C1", "C2"):
            return "A1"
        return v

    @field_validator("audio_url", "phonetic", "example_sentence", "example_meaning", mode="before")
    @classmethod
    def clean_optional_strings(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned if cleaned else None

    @field_validator("word", "meaning", mode="before")
    @classmethod
    def validate_required_text(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Trường này không được để trống.")
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Trường này không được để trống.")
        return cleaned

    @field_validator("topic_ids", mode="before")
    @classmethod
    def clean_topic_ids(cls, values: Any) -> list[int]:
        if values is None:
            raise ValueError("Vui lòng chọn ít nhất một chủ đề.")
        if isinstance(values, (int, str)):
            values = [values]
        cleaned: list[int] = []
        for v in values:
            try:
                i = int(v)
                if i > 0 and i not in cleaned:
                    cleaned.append(i)
            except (ValueError, TypeError):
                continue
        if not cleaned:
            raise ValueError("Vui lòng chọn ít nhất một chủ đề hợp lệ.")
        return cleaned


class TopicCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language_code: str = Field(pattern=LANG_PATTERN)
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    icon_url: Optional[str] = Field(default=None, max_length=500)
    sort_order: int = Field(default=100, ge=1, le=32767)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Tên chủ đề không được để trống.")
        return cleaned

    @field_validator("description", "icon_url", mode="before")
    @classmethod
    def strip_optional_text(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class TopicUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language_code: Optional[str] = Field(default=None, pattern=LANG_PATTERN)
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    icon_url: Optional[str] = Field(default=None, max_length=500)
    sort_order: Optional[int] = Field(default=None, ge=1, le=32767)

    @field_validator("name", mode="before")
    @classmethod
    def check_name(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Tên chủ đề không được để trống.")
        return cleaned

    @field_validator("description", "icon_url", mode="before")
    @classmethod
    def check_optional(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None
