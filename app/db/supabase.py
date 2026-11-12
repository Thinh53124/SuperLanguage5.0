"""
Hai loại client Supabase, KHÔNG dùng lẫn lộn:

- supabase_admin : dùng secret key, chỉ để đọc/ghi database (bỏ qua RLS).
                   KHÔNG BAO GIỜ gọi sign_in / sign_up / verify_otp trên client này,
                   vì supabase-py sẽ gắn token của user vào client và các request
                   sau đó sẽ chạy với quyền của user đó.
- new_auth_client(): tạo client mới cho MỖI request đăng ký/đăng nhập/OTP,
                   dùng publishable key, không lưu session.
"""

import httpx
from supabase import Client, create_client

try:  # supabase-py mới: lớp dành cho client đồng bộ (có httpx_client)
    from supabase.lib.client_options import SyncClientOptions as ClientOptions
except ImportError:  # supabase-py cũ
    from supabase.lib.client_options import ClientOptions  # type: ignore[assignment]

from app.core.config import settings


# httpx mặc định chỉ chờ 5 giây. Đăng ký/OTP phải đợi Supabase gửi email nên
# dễ bị ReadTimeout; nới lên 30 giây cho các request xác thực.
AUTH_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _options(auth_timeout: bool = False) -> ClientOptions:
    kwargs = {}
    # Chỉ truyền httpx_client nếu phiên bản supabase-py đang cài hỗ trợ
    if auth_timeout and "httpx_client" in getattr(ClientOptions, "__dataclass_fields__", {}):
        kwargs["httpx_client"] = httpx.Client(timeout=AUTH_TIMEOUT, follow_redirects=True)
    return ClientOptions(auto_refresh_token=False, persist_session=False, **kwargs) # type: ignore


supabase_admin: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SECRET_KEY,
    options=_options(),
)


def new_auth_client() -> Client:
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_PUBLISHABLE_KEY,
        options=_options(auth_timeout=True),
    )