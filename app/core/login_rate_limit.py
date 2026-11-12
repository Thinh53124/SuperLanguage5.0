import hashlib
import hmac
import logging

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.db.supabase import supabase_admin

logger = logging.getLogger(__name__)


def _bucket_key(value: str) -> str:
    return hmac.new(
        settings.SUPABASE_SECRET_KEY.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def check_login_rate_limit(request: Request, email: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    normalized_email = email.strip().lower()
    try:
        result = supabase_admin.rpc(
            "consume_login_attempts",
            {
                "p_email_ip_key": _bucket_key(f"email:{normalized_email}|ip:{client_ip}"),
                "p_ip_key": _bucket_key(f"ip:{client_ip}"),
            },
        ).execute()
    except Exception as exc:
        logger.exception("Could not enforce the login rate limit.")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Không thể kiểm tra giới hạn đăng nhập lúc này. Vui lòng thử lại sau.",
        ) from exc

    if (
        not isinstance(result.data, list)
        or not result.data
        or not isinstance(result.data[0], dict)
        or not isinstance(result.data[0].get("allowed"), bool)
    ):
        logger.error("Login rate-limit function returned an invalid response.")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Không thể kiểm tra giới hạn đăng nhập lúc này. Vui lòng thử lại sau.",
        )

    decision = result.data[0]
    if not decision["allowed"]:
        retry_after = max(1, int(decision.get("retry_after") or 1)) # type: ignore
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Bạn đã vượt quá số lượt đăng nhập cho phép. Vui lòng thử lại sau.",
            headers={"Retry-After": str(retry_after)},
        )
