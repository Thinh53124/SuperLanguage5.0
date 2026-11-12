"""
Xác thực JWT do Supabase Auth cấp.

Cài đặt thư viện:
    pip uninstall python-jose
    pip install "pyjwt[crypto]"

Biến môi trường cần có trong .env:
    SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
"""

import logging
from typing import Any, Dict, Optional

import jwt
from jwt import PyJWKClient, PyJWTError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Các thuật toán ký bất đối xứng mà Supabase hỗ trợ
SUPPORTED_ALGORITHMS = ["ES256", "RS256"]

# Tạo client một lần duy nhất để cache public key (tránh gọi JWKS endpoint mỗi request)
_jwks_client: Optional[PyJWKClient] = (
    PyJWKClient(settings.SUPABASE_JWKS_URL) if settings.SUPABASE_JWKS_URL else None
)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Giải mã và verify access token do Supabase Auth phát hành.

    Trả về payload (dict) nếu token hợp lệ, ngược lại trả về None.
    """
    if not token:
        return None

    if _jwks_client is None:
        logger.error("SUPABASE_JWKS_URL chưa được cấu hình trong .env")
        return None

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=SUPPORTED_ALGORITHMS,
            audience="authenticated",
        )
    except PyJWTError as exc:
        # Gồm: token hết hạn, sai chữ ký, sai audience, không lấy được JWKS...
        logger.warning("JWT verification failed: %s", exc)
        return None