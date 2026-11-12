from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.db.supabase import supabase_admin
from app.services.profile_service import raise_db_error


def get_admin_overview_stats() -> Dict[str, Any]:
    """Lấy dữ liệu thống kê tổng hợp thực tế từ các bảng Supabase."""
    try:
        # 1. Đếm tổng số học viên
        profiles_res = supabase_admin.table("profiles").select("id, target_language, role, status, plan_id", count="exact").execute()
        total_students = profiles_res.count or len(profiles_res.data or [])

        # 2. Đếm tổng số từ vựng
        words_res = supabase_admin.table("words").select("id", count="exact").execute()
        total_words = words_res.count or len(words_res.data or [])

        # 3. Đếm tổng số chủ đề
        topics_res = supabase_admin.table("topics").select("id, language_code", count="exact").execute()
        total_topics = topics_res.count or len(topics_res.data or [])

        # 4. Tính toán tổng XP và thống kê streak
        stats_res = supabase_admin.table("user_stats").select("xp_total, words_learned, current_streak, longest_streak").execute()
        user_stats_data = stats_res.data or []
        total_xp = sum(item.get("xp_total", 0) for item in user_stats_data)
        max_streak = max((item.get("longest_streak", 0) for item in user_stats_data), default=0)

        # 5. Phân bổ ngôn ngữ học tập
        lang_distribution: Dict[str, int] = {}
        for p in profiles_res.data or []:
            lang = p.get("target_language") or "en"
            lang_distribution[lang] = lang_distribution.get(lang, 0) + 1

        return {
            "total_students": total_students,
            "total_words": total_words,
            "total_topics": total_topics,
            "total_xp": total_xp,
            "max_streak": max_streak,
            "language_distribution": lang_distribution,
        }
    except Exception as exc:
        raise_db_error(exc)
        return {}


def list_admin_topics_full(language_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách chủ đề và đếm số từ vựng liên kết thực tế."""
    try:
        query = supabase_admin.table("topics").select("id, language_code, name, description, icon_url, sort_order")
        if language_code and language_code != "all":
            query = query.eq("language_code", language_code)
        
        topics = query.order("sort_order").execute().data or []

        # Lấy số từ vựng cho từng chủ đề qua bảng word_topics
        topic_ids = [t["id"] for t in topics]
        word_count_map: Dict[int, int] = {}
        if topic_ids:
            wt_res = supabase_admin.table("word_topics").select("topic_id").in_("topic_id", topic_ids).execute()
            for row in wt_res.data or []:
                tid = row["topic_id"]
                word_count_map[tid] = word_count_map.get(tid, 0) + 1

        for t in topics:
            t["word_count"] = word_count_map.get(t["id"], 0)

        return topics
    except Exception as exc:
        raise_db_error(exc)
        return []


def create_admin_topic(data: Dict[str, Any]) -> Dict[str, Any]:
    """Tạo chủ đề mới trong CSDL."""
    try:
        res = supabase_admin.table("topics").insert({
            "language_code": data["language_code"],
            "name": data["name"],
            "description": data.get("description"),
            "icon_url": data.get("icon_url") or "category",
            "sort_order": data.get("sort_order", 100),
        }).execute()

        if not res.data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Không thể tạo chủ đề.")
        return res.data[0]
    except Exception as exc:
        raise_db_error(exc)
        raise


def update_admin_topic(topic_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cập nhật thông tin chủ đề theo ID."""
    clean_data = {k: v for k, v in data.items() if v is not None}
    if not clean_data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Không có trường nào được gửi để cập nhật.")

    try:
        res = supabase_admin.table("topics").update(clean_data).eq("id", topic_id).execute()
        if not res.data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy chủ đề.")
        return res.data[0]
    except Exception as exc:
        raise_db_error(exc)
        raise


def delete_admin_topic(topic_id: int) -> None:
    """Xóa một chủ đề khỏi hệ thống."""
    try:
        res = supabase_admin.table("topics").delete().eq("id", topic_id).execute()
        if not res.data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy chủ đề cần xóa.")
    except Exception as exc:
        raise_db_error(exc)


def list_admin_users(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """Lấy danh sách người dùng và thống kê học tập."""
    try:
        res = (
            supabase_admin.table("profiles")
            .select(
                "id, email, username, display_name, role, status, plan_id, target_language, current_level, created_at",
                count="exact",
            )
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        profiles = res.data or []
        total = res.count or len(profiles)

        user_ids = [p["id"] for p in profiles]
        stats_map: Dict[str, Dict[str, Any]] = {}
        if user_ids:
            stats_res = (
                supabase_admin.table("user_stats")
                .select("user_id, xp_total, current_streak, longest_streak, words_learned")
                .in_("user_id", user_ids)
                .execute()
            )
            for s in stats_res.data or []:
                stats_map[s["user_id"]] = s

        for p in profiles:
            st = stats_map.get(p["id"], {})
            p["xp_total"] = st.get("xp_total", 0)
            p["current_streak"] = st.get("current_streak", 0)
            p["words_learned"] = st.get("words_learned", 0)

        return {"items": profiles, "total": total, "limit": limit, "offset": offset}
    except Exception as exc:
        raise_db_error(exc)
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

