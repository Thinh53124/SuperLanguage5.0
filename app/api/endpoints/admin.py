from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import get_current_admin_profile
from app.schemas.vocabulary import TopicCreate, TopicUpdate, WordCreate
from app.services.admin import (
    create_admin_topic,
    delete_admin_topic,
    get_admin_overview_stats,
    list_admin_topics_full,
    list_admin_users,
    update_admin_topic,
)
from app.services.vocabulary_service import (
    create_word,
    delete_word as delete_word_record,
    get_admin_word,
    list_admin_languages,
    list_admin_words,
    update_word as update_word_record,
)

router = APIRouter()


@router.get("/stats")
def get_stats(_: Dict[str, Any] = Depends(get_current_admin_profile)):
    """Lấy dữ liệu thống kê tổng quan thực tế từ CSDL."""
    return {"status": "success", "data": get_admin_overview_stats()}


@router.get("/users")
def get_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Danh sách học viên và người dùng kèm số liệu học tập thực tế."""
    return list_admin_users(limit, offset)


# ==================== TOPICS MANAGEMENT ====================

@router.get("/topics")
def get_topics(
    language_code: Optional[str] = Query(default=None),
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Lấy danh sách các chủ đề (kèm đếm số từ vựng thật trong từng chủ đề)."""
    return {"items": list_admin_topics_full(language_code)}


@router.post("/topics", status_code=status.HTTP_201_CREATED)
def add_topic(
    body: TopicCreate,
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Admin tạo một chủ đề mới trong CSDL."""
    topic = create_admin_topic(body.model_dump(mode="json"))
    return {"status": "success", "topic": topic}


@router.put("/topics/{topic_id}", status_code=status.HTTP_200_OK)
def update_topic(
    topic_id: int,
    body: TopicUpdate,
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Admin cập nhật thông tin chủ đề theo ID."""
    topic = update_admin_topic(topic_id, body.model_dump(mode="json", exclude_unset=True))
    return {"status": "success", "topic": topic}


@router.delete("/topics/{topic_id}", status_code=status.HTTP_200_OK)
def delete_topic(
    topic_id: int,
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Admin xóa một chủ đề theo ID."""
    delete_admin_topic(topic_id)
    return {"status": "success", "deleted_topic_id": topic_id}


# ==================== WORDS & LANGUAGES ====================

@router.get("/words")
def get_words(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Danh sách từ vựng dành cho quản trị viên."""
    return list_admin_words(limit, offset)


@router.get("/words/{word_id}")
def get_word(
    word_id: int,
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Chi tiết từ vựng, bao gồm các chủ đề đang liên kết."""
    return {"status": "success", "word": get_admin_word(word_id)}


@router.get("/languages")
def get_languages(_: Dict[str, Any] = Depends(get_current_admin_profile)):
    return {"items": list_admin_languages()}


@router.post("/words", status_code=status.HTTP_201_CREATED)
def add_word(
    body: WordCreate,
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Admin tạo một từ vựng mới và gắn từ đó với các chủ đề cùng ngôn ngữ."""
    return {"status": "success", "word": create_word(body.model_dump(mode="json"))}


@router.delete("/words/{word_id}", status_code=status.HTTP_200_OK)
def delete_word(
    word_id: int,
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Admin xóa một từ vựng theo ID."""
    delete_word_record(word_id)
    return {"status": "success", "deleted_word_id": word_id}


@router.put("/words/{word_id}", status_code=status.HTTP_200_OK)
def update_word(
    word_id: int,
    body: WordCreate,
    _: Dict[str, Any] = Depends(get_current_admin_profile),
):
    """Admin cập nhật thông tin một từ vựng theo ID."""
    word = update_word_record(word_id, body.model_dump(mode="json"))
    return {"status": "success", "word": word}
