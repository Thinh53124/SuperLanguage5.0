from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.supabase import supabase_admin
from app.api.endpoints import learning_activity
from app.api.endpoints import admin, auth, users, vocabulary, chat_ai



from app.core.exception import AppException
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Cấu hình CORS Middleware cho phép kết nối từ Frontend (Vite/React/HTML)
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Tích hợp Auth Router vào hệ thống API 
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/me", tags=["me"])
app.include_router(chat_ai.router, prefix=f"{settings.API_V1_STR}/chat-ai", tags=["Chat_AI"])
app.include_router(
    vocabulary.router,
    prefix=f"{settings.API_V1_STR}/vocabulary",
    tags=["vocabulary"],
)
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(
    learning_activity.router,
    prefix=f"{settings.API_V1_STR}/learning",
    tags=["Learning Activity"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": f"Welcome to {settings.PROJECT_NAME} API!",
        "version": settings.VERSION,
    }


@app.get("/test-supabase")
def test_supabase_connection():
    try:
        supabase_admin.auth.get_session()
        return {
            "status": "success",
            "message": "Kết nối Supabase thành công!",
            "supabase_url": settings.SUPABASE_URL,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi kết nối Supabase: {str(e)}"
        )
        
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "data": None,
            "error": {
                "code": exc.error_code,
                "detail": str(exc)
            }
        }
    )