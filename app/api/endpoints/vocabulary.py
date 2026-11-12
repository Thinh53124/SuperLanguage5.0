from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_profile
from app.services.vocabulary_service import list_topics, list_words

router = APIRouter()


@router.get("/topics")
def get_topics(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Dict[str, Any] = Depends(get_current_profile),
):
    """Danh sách chủ đề theo ngôn ngữ đang học và gói hiện tại."""
    return list_topics(profile, limit, offset)


@router.get("/words")
def get_words(
    topic_id: Optional[int] = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Dict[str, Any] = Depends(get_current_profile),
):
    """Danh sách từ vựng trong ngôn ngữ đang học, có thể lọc theo chủ đề."""
    return list_words(profile, limit, offset, topic_id)
