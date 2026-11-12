from datetime import date, time
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LANG_PATTERN = r"^[a-z]{2,3}$"

Level = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
Goal = Literal["travel", "work", "study", "exam", "hobby", "other"]


def _check_timezone(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    try:
        ZoneInfo(v)
    except Exception:
        raise ValueError("Múi giờ không hợp lệ (ví dụ: Asia/Ho_Chi_Minh).")
    return v


def _normalize_country(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip().upper()
    if len(v) != 2 or not v.isalpha():
        raise ValueError("Mã quốc gia phải gồm 2 chữ cái (ví dụ: VN).")
    return v


class ProfileUpdate(BaseModel):
    """PATCH /me: chỉ cập nhật các trường được gửi lên."""

    model_config = ConfigDict(extra="forbid")

    username: Optional[str] = Field(default=None, pattern=r"^[a-z0-9_]{3,30}$")
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    avatar_url: Optional[str] = Field(default=None, max_length=500, pattern=r"^https://")
    birth_year: Optional[int] = Field(default=None, ge=1900, le=date.today().year)
    country_code: Optional[str] = None
    timezone: Optional[str] = None
    native_language: Optional[str] = Field(default=None, pattern=LANG_PATTERN)
    target_language: Optional[str] = Field(default=None, pattern=LANG_PATTERN)
    current_level: Optional[Level] = None
    target_level: Optional[Level] = None
    learning_goal: Optional[Goal] = None
    daily_goal_xp: Optional[int] = Field(default=None, ge=10, le=500)
    reminder_time: Optional[time] = None
    marketing_opt_in: Optional[bool] = None
    show_on_leaderboard: Optional[bool] = None

    _tz = field_validator("timezone")(_check_timezone)
    _country = field_validator("country_code")(_normalize_country)


class OnboardingRequest(BaseModel):
    """POST /me/onboarding: bước chọn ngôn ngữ, trình độ, mục tiêu sau khi đăng ký."""

    model_config = ConfigDict(extra="forbid")

    native_language: str = Field(pattern=LANG_PATTERN)
    target_language: str = Field(pattern=LANG_PATTERN)
    current_level: Level
    target_level: Level
    learning_goal: Goal
    daily_goal_xp: int = Field(default=20, ge=10, le=500)
    timezone: str = "Asia/Ho_Chi_Minh"
    country_code: Optional[str] = None
    reminder_time: Optional[time] = None

    _tz = field_validator("timezone")(_check_timezone)
    _country = field_validator("country_code")(_normalize_country)

    @model_validator(mode="after")
    def check_business_rules(self) -> "OnboardingRequest":
        if self.native_language == self.target_language:
            raise ValueError("Ngôn ngữ mẹ đẻ và ngôn ngữ muốn học phải khác nhau.")
        if LEVEL_ORDER.index(self.target_level) < LEVEL_ORDER.index(self.current_level):
            raise ValueError("Trình độ mục tiêu không được thấp hơn trình độ hiện tại.")
        return self