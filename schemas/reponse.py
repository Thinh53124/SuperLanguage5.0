from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    status: str = "Success"
    message: str = "Thành công"
    data: Optional[T] = None
    error: Optional[Any] = None
