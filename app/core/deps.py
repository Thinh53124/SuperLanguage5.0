from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.services.profile_service import get_profile

bearer_scheme = HTTPBearer(auto_error=False)


def get_bearer_token(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Thiếu hoặc sai header Authorization.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return creds.credentials


def get_current_user(token: str = Depends(get_bearer_token)) -> Dict[str, Any]:
    """Verify JWT của Supabase, trả về payload (có 'sub' là user id)."""
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_profile(payload: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Lấy profile của user hiện tại và chặn tài khoản bị khóa/đã xóa."""
    profile = get_profile(payload["sub"])
    if profile is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại.")
    if profile["status"] != "active" or profile.get("deleted_at"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa hoặc vô hiệu hóa.")
    return profile


def get_current_admin_profile(
    profile: Dict[str, Any] = Depends(get_current_profile),
) -> Dict[str, Any]:
    """Chỉ cho phép tài khoản admin đang hoạt động truy cập API quản trị."""
    if profile.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không có quyền quản trị.")
    return profile