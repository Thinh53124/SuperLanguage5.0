from typing import Any, Dict

from fastapi import HTTPException, status

from app.db.supabase import supabase_admin
from app.services.profile_service import raise_db_error

XP_PER_LESSON = 20

def record_lesson_activity(
    user_id: int,
    lesson_id: int,
) -> Dict[str, Any]:
    try:
        result = supabase_admin.rpc(
            "complete_lesson_and_award_xp",
            {
                "p_user_id": user_id,
                "p_lesson_id": lesson_id,
                "p_xp_amount": XP_PER_LESSON,
            },
        ).execute()
    except Exception as exc:
        raise_db_error(exc)

    data = result.data

    if isinstance(data, list):
        data = data[0] if data else None

    if not data:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Không thể ghi nhận hoạt động học tập.",
        )

    return {
        "success": True,
        "xp_earned": data["xp_earned"],
        "total_xp": data["total_xp"],
        "current_level": data["current_level"],
        "leveled_up": data["leveled_up"],
        "message": data["message"],
    }
