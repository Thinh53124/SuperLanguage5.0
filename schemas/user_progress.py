
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserProgressBase(BaseModel):
    user_id: int
    course_id: int
    completed_lessons: int = Field(default=0, ge=0)
    total_lessons: int = Field(default=0, ge=0)


class UserProgressCreate(UserProgressBase):
    pass


class UserProgressUpdate(BaseModel):
    completed_lessons: int | None = Field(default=None, ge=0)
    total_lessons: int | None = Field(default=None, ge=0)


class UserProgressOut(UserProgressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_accessed_at: datetime | None
    created_at: datetime
    updated_at: datetime
