from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

LANG_PATTERN = r"^[a-z]{2,3}$"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=50)
    native_language: str = Field(default="vi", pattern=LANG_PATTERN)
    target_language: str = Field(default="en", pattern=LANG_PATTERN)
    accept_terms: bool

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("accept_terms")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Bạn cần đồng ý với điều khoản sử dụng.")
        return v

    @model_validator(mode="after")
    def languages_must_differ(self) -> "RegisterRequest":
        if self.native_language == self.target_language:
            raise ValueError("Ngôn ngữ mẹ đẻ và ngôn ngữ muốn học phải khác nhau.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class EmailRequest(BaseModel):
    email: EmailStr


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    token: str = Field(pattern=r"^\d{6,10}$")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)