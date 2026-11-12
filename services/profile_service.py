import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, NoReturn, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.db.supabase import supabase_admin

logger = logging.getLogger(__name__)

# Chỉ các trường hồ sơ/cài đặt thông thường mới được phép sửa qua PATCH /me.
PROFILE_UPDATE_FIELDS = frozenset(
    {
        "username",
        "display_name",
        "avatar_url",
        "birth_year",
        "country_code",
        "timezone",
        "native_language",
        "target_language",
        "current_level",
        "target_level",
        "learning_goal",
        "daily_goal_xp",
        "reminder_time",
        "marketing_opt_in",
        "show_on_leaderboard",
    }
)

ONBOARDING_FIELDS = frozenset(
    {
        "native_language",
        "target_language",
        "current_level",
        "target_level",
        "learning_goal",
        "daily_goal_xp",
        "timezone",
        "country_code",
        "reminder_time",
    }
)

# Các cột NOT NULL: nếu client gửi null thì bỏ qua thay vì để DB báo lỗi
NOT_NULLABLE_FIELDS = {
    "username",
    "native_language",
    "target_language",
    "daily_goal_xp",
    "timezone",
    "marketing_opt_in",
    "show_on_leaderboard",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def raise_db_error(exc: Exception) -> NoReturn:
    """Đổi lỗi database thành HTTPException dễ hiểu, log lỗi gốc."""
    logger.warning("Database error: %s", exc)
    code = str(getattr(exc, "code", "") or "")
    text = str(exc).lower()

    if code == "23505" or "duplicate key" in text:
        raise HTTPException(status.HTTP_409_CONFLICT, "Tên đăng nhập (username) đã được sử dụng.")
    if code in ("23514", "23503") or "violates check constraint" in text or "foreign key" in text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Dữ liệu không hợp lệ.")
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Không thể cập nhật dữ liệu.")


def validate_languages(native: Optional[str], target: Optional[str]) -> None:
    """Kiểm tra mã ngôn ngữ có tồn tại và được phép chọn trong bảng languages."""
    codes = [c for c in (native, target) if c]
    if not codes:
        return

    rows = (
        supabase_admin.table("languages")
        .select("code,is_learnable,is_native_supported")
        .in_("code", codes)
        .execute()
        .data
    )
    by_code = {r["code"]: r for r in rows} # type: ignore

    if native:
        row = by_code.get(native)
        if not row or not row["is_native_supported"]: # type: ignore
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Ngôn ngữ mẹ đẻ này chưa được hỗ trợ."
            )
    if target:
        row = by_code.get(target)
        if not row or not row["is_learnable"]: # type: ignore
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Ngôn ngữ muốn học này chưa được hỗ trợ."
            )
    if native and target and native == target:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Ngôn ngữ mẹ đẻ và ngôn ngữ muốn học phải khác nhau.",
        )


def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    rows = supabase_admin.table("profiles").select("*").eq("id", user_id).limit(1).execute().data
    return rows[0] if rows else None  # type: ignore[return-value]


def get_stats(user_id: str) -> Dict[str, Any]:
    rows = supabase_admin.table("user_stats").select("*").eq("user_id", user_id).limit(1).execute().data
    return rows[0] if rows else {}  # type: ignore[return-value]


def get_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    rows = supabase_admin.table("plans").select("*").eq("id", plan_id).limit(1).execute().data
    return rows[0] if rows else None  # type: ignore[return-value]


def user_today(tz_name: str) -> date:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date()


def with_effective_streak(stats: Dict[str, Any], tz_name: str) -> Dict[str, Any]:
    """
    Chuỗi trong DB chỉ được đóng khi user học lần kế tiếp. Khi hiển thị,
    nếu đã bỏ lỡ hơn 1 ngày thì coi chuỗi hiện tại là 0.
    """
    result = dict(stats)
    last = stats.get("last_activity_date")
    studied_today = False
    effective = 0

    if last:
        today = user_today(tz_name)
        gap = (today - date.fromisoformat(last)).days
        studied_today = gap == 0
        if gap <= 1:
            effective = int(stats.get("current_streak", 0))

    result["current_streak"] = effective
    result["studied_today"] = studied_today
    return result


def _update_profile(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    clean = {k: v for k, v in data.items() if not (v is None and k in NOT_NULLABLE_FIELDS)}
    if not clean:
        profile = get_profile(user_id)
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy hồ sơ.")
        return profile

    try:
        res = supabase_admin.table("profiles").update(clean).eq("id", user_id).execute()
    except Exception as exc:
        raise_db_error(exc)

    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy hồ sơ.")
    return res.data[0]  # type: ignore[return-value]


def _ensure_allowed_fields(data: Dict[str, Any], allowed_fields: frozenset[str]) -> None:
    forbidden_fields = data.keys() - allowed_fields
    if forbidden_fields:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Có trường hồ sơ không được phép cập nhật.",
        )


def update_profile(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cập nhật hồ sơ của user hiện tại với allowlist trường dành cho PATCH /me."""
    _ensure_allowed_fields(data, PROFILE_UPDATE_FIELDS)
    validate_languages(data.get("native_language"), data.get("target_language"))
    return _update_profile(user_id, data)


def complete_onboarding(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Ghi dữ liệu onboarding và thời điểm hoàn tất do backend tự tạo."""
    _ensure_allowed_fields(data, ONBOARDING_FIELDS)
    validate_languages(data.get("native_language"), data.get("target_language"))
    return _update_profile(user_id, {**data, "onboarding_completed_at": now_iso()})


def touch_last_sign_in(user_id: str) -> None:
    try:
        supabase_admin.table("profiles").update({"last_sign_in_at": now_iso()}).eq("id", user_id).execute()
    except Exception:
        logger.exception("Không cập nhật được last_sign_in_at cho %s", user_id)