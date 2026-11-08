
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class XpLogBase(BaseModel):
    user_id: int
    source: str = Field(min_length=1, max_length=100)
    xp_amount: int = Field(ge=0)


class XpLogCreate(XpLogBase):
    pass


class XpLogOut(XpLogBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
