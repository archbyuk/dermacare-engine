from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import jwt
import secrets
import os
from db.session import get_db
from db.models.users import Users

router = APIRouter(prefix="/auth", tags=["인증"])

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user_id: int = None
    access_token: str = None
    refresh_token: str = None
    role: str = None

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str


# 액세스 토큰 생성
def generate_access_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc)
    }
    # 환경변수에서 시크릿 키 가져오기
    secret_key = os.getenv("JWT_SECRET_KEY", "dermacare_secret_key_2024")
    return jwt.encode(payload, secret_key, algorithm="HS256")


# 리프레시 토큰 생성 (랜덤 문자열)
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


"""
    JWT 로그인

    사용자 로그인 API (JWT 토큰 생성)
"""
@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        # 사용자 조회
        user = db.query(Users).filter(Users.Username == request.username).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
        
        # 비밀번호 확인 (간단한 문자열 비교)
        if user.Password != request.password:
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")
        
        # JWT 토큰 생성
        access_token = generate_access_token(user.ID, user.Username, user.Role)
        refresh_token = generate_refresh_token()
        
        # 리프레시 토큰 만료 시간 설정 (7일)
        refresh_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        # 데이터베이스에 토큰 정보 저장
        user.Access_Token = access_token
        user.Refresh_Token = refresh_token
        user.Token_Expires_At = refresh_expires  # 리프레시 토큰 만료 시간 사용
        user.Last_Login_At = datetime.now(timezone.utc)
        
        # Set-Cookie 헤더 설정
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=3600,  # 1시간
            httponly=True,  # XSS 방지
            secure=False,   # HTTPS 사용 시 True로 변경
            samesite="lax"  # CSRF 방지
        )
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=7*24*3600,  # 7일
            httponly=True,
            secure=False,
            samesite="lax"
        )
        
        db.commit()
        
        return LoginResponse(
            success=True,
            message="로그인 성공",
            user_id=user.ID,
            access_token=access_token,  # body에도 포함 (호환성)
            refresh_token=refresh_token,  # body에도 포함 (호환성)
            role=user.Role
        )
        
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 중 오류가 발생했습니다: {str(e)}")


"""
    JWT 리프레시 토큰

    리프레시 토큰으로 새로운 액세스 토큰 발급
"""
@router.post("/refresh", response_model=LoginResponse)
def refresh_token(request: RefreshRequest, response: Response, db: Session = Depends(get_db)):
    try:
        # 리프레시 토큰으로 사용자 조회
        user = db.query(Users).filter(
            Users.Refresh_Token == request.refresh_token,
            Users.Token_Expires_At > datetime.now(timezone.utc)  # 만료되지 않은 토큰만
        ).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다")
        
        # 새로운 액세스 토큰 생성
        access_token = generate_access_token(user.ID, user.Username, user.Role)
        
        # 데이터베이스 업데이트
        user.Access_Token = access_token
        db.commit()
        
        # 새로운 액세스 토큰을 쿠키에 설정
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=3600,  # 1시간
            httponly=True,
            secure=False,
            samesite="lax"
        )
        
        return LoginResponse(
            success=True,
            message="토큰 갱신 성공",
            user_id=user.ID,
            access_token=access_token,
            refresh_token=user.Refresh_Token,  # 기존 리프레시 토큰 유지
            role=user.Role
        )
        
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"토큰 갱신 중 오류가 발생했습니다: {str(e)}")


"""
    로그아웃

    토큰 무효화
"""
@router.post("/logout")
def logout(request: LogoutRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user = db.query(Users).filter(Users.Refresh_Token == request.refresh_token).first()
        
        if user:
            # 토큰 정보 초기화
            user.Access_Token = None
            user.Refresh_Token = None
            user.Token_Expires_At = None
            db.commit()
        
        # 쿠키 삭제
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return {"success": True, "message": "로그아웃 완료"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그아웃 중 오류가 발생했습니다: {str(e)}")
