from pydantic import BaseModel


class LessonCompleteResponse(BaseModel):
    success: bool
    xp_earned: int
    total_xp: int
    current_level: int
    leveled_up: bool
    message: str
