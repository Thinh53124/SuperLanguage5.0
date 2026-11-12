import logging
from typing import Any, Dict, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.deps import get_bearer_token
from app.core.login_rate_limit import check_login_rate_limit
from app.db.supabase import new_auth_client, supabase_admin
from app.schemas.auth import (
    EmailRequest,
    LoginRequest,
    OTPVerifyRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.services.profile_service import (
    get_profile,
    now_iso,
    touch_last_sign_in,
    validate_languages,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _raise_auth_error(exc: Exception, default_status: int, default_msg: str) -> NoReturn:
    """Đổi lỗi Supabase Auth thành thông báo thân thiện; lỗi gốc chỉ ghi log."""
    upstream_status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    exception_name = type(exc).__name__.lower()
    logger.warning(
        "Supabase Auth request failed (exception=%s, upstream_status=%s)",
        type(exc).__name__,
        upstream_status,
    )
    msg = str(exc).lower()

    if upstream_status == status.HTTP_429_TOO_MANY_REQUESTS or any(
        text in msg for text in ("rate limit", "too many", "security purposes")
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút.",
        ) from exc

    is_upstream_error = isinstance(upstream_status, int) and upstream_status >= 500
    is_transient_error = any(
        text in exception_name for text in ("retryable", "timeout", "connection", "network")
    )
    if is_upstream_error or is_transient_error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Dịch vụ xác thực đang tạm thời không khả dụng. Vui lòng thử lại sau.",
        ) from exc

    if "already registered" in msg or "already been registered" in msg:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email này đã được đăng ký.") from exc
    if "not confirmed" in msg:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Email chưa được xác thực. Vui lòng kiểm tra hộp thư."
        ) from exc
    if "password" in msg and any(w in msg for w in ("weak", "least", "short", "characters")):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Mật khẩu chưa đủ mạnh.") from exc
    raise HTTPException(default_status, default_msg) from exc


def _tokens(session: Any) -> Dict[str, Any]:
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": session.expires_in,
    }


def _session_response(session: Any, user_id: str, require_admin: bool = False) -> Dict[str, Any]:
    """Kiểm tra tài khoản còn hoạt động, ghi nhận đăng nhập, trả token + tóm tắt hồ sơ."""
    profile = get_profile(user_id)
    if profile is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản chưa được khởi tạo hồ sơ.")
    if profile["status"] != "active" or profile.get("deleted_at"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa hoặc vô hiệu hóa.")
    if require_admin and profile["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản không có quyền truy cập trang quản trị.")

    touch_last_sign_in(user_id)

    return {
        "status": "success",
        **_tokens(session),
        "user": {
            "id": profile["id"],
            "email": profile["email"],
            "username": profile["username"],
            "display_name": profile["display_name"],
            "avatar_url": profile["avatar_url"],
            "role": profile["role"],
            "plan_id": profile["plan_id"],
        },
        "needs_onboarding": profile["onboarding_completed_at"] is None,
    }


# ---------------------------------------------------------------------
# Đăng ký
# ---------------------------------------------------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest):
    """
    Đăng ký tài khoản:
    1. Kiểm tra ngôn ngữ hợp lệ (trước khi tạo user, tránh tạo xong mới lỗi).
    2. Tạo user ở Supabase Auth -> trigger tự tạo profiles + user_stats.
    3. Ghi ngôn ngữ đã chọn và thời điểm đồng ý điều khoản vào profiles.
    """
    validate_languages(data.native_language, data.target_language)

    metadata: Dict[str, Any] = {}
    if data.display_name:
        metadata["display_name"] = data.display_name

    client = new_auth_client()
    try:
        response = client.auth.sign_up(
            {
                "email": str(data.email),
                "password": data.password,
                "options": {"data": metadata},
            }
        )
    except Exception as exc:
        _raise_auth_error(exc, status.HTTP_400_BAD_REQUEST, "Đăng ký thất bại. Vui lòng thử lại.")

    user = response.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Đăng ký thất bại. Vui lòng thử lại.")

    # Khi bật "Confirm email", email đã tồn tại sẽ trả về user giả với identities rỗng
    if user.identities is not None and len(user.identities) == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email này đã được đăng ký.")

    try:
        supabase_admin.table("profiles").update(
            {
                "native_language": data.native_language,
                "target_language": data.target_language,
                "terms_accepted_at": now_iso(),
            }
        ).eq("id", user.id).execute()
    except Exception:
        # Không làm hỏng đăng ký; người dùng vẫn chọn lại được ở bước onboarding
        logger.exception("Không ghi được ngôn ngữ/điều khoản cho user %s", user.id)

    result: Dict[str, Any] = {
        "status": "success",
        "message": (
            "Đăng ký thành công! Vui lòng kiểm tra email để xác thực tài khoản."
            if response.session is None
            else "Đăng ký thành công!"
        ),
        "user_id": user.id,
        "email": user.email,
        "email_confirmation_required": response.session is None,
        "needs_onboarding": True,
    }
    if response.session is not None:
        result.update(_tokens(response.session))
    return result


# ---------------------------------------------------------------------
# Đăng nhập / làm mới token / đăng xuất
# ---------------------------------------------------------------------
@router.post("/login")
def login(data: LoginRequest, request: Request):
    check_login_rate_limit(request, str(data.email))
    client = new_auth_client()
    try:
        response = client.auth.sign_in_with_password(
            {"email": str(data.email), "password": data.password}
        )
    except Exception as exc:
        _raise_auth_error(exc, status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không chính xác.")

    if not response.session or not response.user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không chính xác.")

    return _session_response(response.session, response.user.id)


@router.post("/admin/login")
def admin_login(data: LoginRequest, request: Request):
    """Đăng nhập riêng cho trang quản trị; chỉ trả token cho tài khoản admin."""
    check_login_rate_limit(request, str(data.email))
    client = new_auth_client()
    try:
        response = client.auth.sign_in_with_password(
            {"email": str(data.email), "password": data.password}
        )
    except Exception as exc:
        _raise_auth_error(exc, status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không chính xác.")

    if not response.session or not response.user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không chính xác.")

    return _session_response(response.session, response.user.id, require_admin=True)


@router.post("/refresh")
def refresh(data: RefreshRequest):
    client = new_auth_client()
    try:
        response = client.auth.refresh_session(data.refresh_token)
    except Exception as exc:
        _raise_auth_error(
            exc,
            status.HTTP_401_UNAUTHORIZED,
            "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        )

    if not response.session:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại."
        )
    return {"status": "success", **_tokens(response.session)}


@router.post("/logout")
def logout(token: str = Depends(get_bearer_token)):
    """Thu hồi phiên đăng nhập hiện tại."""
    try:
        supabase_admin.auth.admin.sign_out(token, "local")
    except Exception:
        # Token có thể đã hết hạn; client vẫn nên xóa token ở phía mình
        logger.info("Logout: không thu hồi được token (có thể đã hết hạn).")
    return {"status": "success", "message": "Đã đăng xuất."}


# ---------------------------------------------------------------------
# Đăng nhập bằng OTP (chỉ cho tài khoản đã tồn tại)
# ---------------------------------------------------------------------
@router.post("/send-otp")
def send_otp(data: EmailRequest):
    client = new_auth_client()
    try:
        client.auth.sign_in_with_otp(
            {"email": str(data.email), "options": {"should_create_user": False}}
        )
    except Exception as exc:
        code = str(getattr(exc, "code", "") or "").lower()
        msg = str(exc).lower()
        if code in {"user_not_found", "email_not_found"} or any(
            text in msg for text in ("user not found", "email not found")
        ):
            logger.info("OTP request ignored for an unregistered email.")
        else:
            _raise_auth_error(
                exc,
                status.HTTP_502_BAD_GATEWAY,
                "Không thể gửi mã OTP lúc này. Vui lòng thử lại sau.",
            )

    return {
        "status": "success",
        "message": "Nếu email hợp lệ, mã OTP đã được gửi tới hộp thư của bạn.",
    }


@router.post("/verify-otp")
def verify_signup_otp(body: OTPVerifyRequest):
    auth_client = new_auth_client()
    try:
        # Xác thực mã OTP 6 chữ số người dùng nhập
        res = auth_client.auth.verify_otp({
            "email": body.email,
            "token": body.token,
            "type": "signup"
        })
        return {"status": "success", "session": res.session}
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Mã OTP không hợp lệ hoặc đã hết hạn.")