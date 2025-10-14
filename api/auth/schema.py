from pydantic import BaseModel

class LoginRequest(BaseModel):
    """로그인 요청 스키마"""
    username: str
    password: str

class LoginResponse(BaseModel):
    """로그인 응답 스키마"""
    success: bool
    message: str
    user_id: int = None
    role: str = None
    username: str = None

class RefreshRequest(BaseModel):
    """리프레시 토큰 요청 스키마"""
    refresh_token: str

class RefreshResponse(BaseModel):
    """리프레시 토큰 응답 스키마"""
    success: bool
    message: str
    user_id: int = None
    role: str = None
    username: str = None

class LogoutRequest(BaseModel):
    """로그아웃 요청 스키마"""
    refresh_token: str