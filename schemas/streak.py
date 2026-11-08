
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class StreakBase(BaseModel):
    user_id: int
    current_streak: int = Field(default=0, ge=0)
    longest_streak: int = Field(default=0, ge=0)
    last_study_date: date | None = None


class StreakCreate(StreakBase):
    pass


class StreakUpdate(BaseModel):
    current_streak: int | None = Field(default=None, ge=0)
    longest_streak: int | None = Field(default=None, ge=0)
    last_study_date: date | None = None


class StreakOut(StreakBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime
