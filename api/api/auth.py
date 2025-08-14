from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import secrets
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


# 액세스 토큰 생성
def generate_access_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    # 실제 운영환경에서는 환경변수로 시크릿 키 관리
    secret_key = "dermacare_secret_key_2024"
    return jwt.encode(payload, secret_key, algorithm="HS256")


# 리프레시 토큰 생성 (랜덤 문자열)
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


"""
    JWT 로그인

    사용자 로그인 API (JWT 토큰 생성)
"""
@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
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
        refresh_expires = datetime.now() + timedelta(days=7)
        
        # 데이터베이스에 토큰 정보 저장
        user.Access_Token = access_token
        user.Refresh_Token = refresh_token
        user.Token_Expires_At = refresh_expires  # 리프레시 토큰 만료 시간 사용
        user.Last_Login_At = datetime.now()
        
        db.commit()
        
        return LoginResponse(
            success=True,
            message="로그인 성공",
            user_id=user.ID,
            access_token=access_token,
            refresh_token=refresh_token,
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
def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    try:
        # 리프레시 토큰으로 사용자 조회
        user = db.query(Users).filter(
            Users.Refresh_Token == request.refresh_token,
            Users.Token_Expires_At > datetime.now()  # 만료되지 않은 토큰만
        ).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다")
        
        # 새로운 액세스 토큰 생성
        access_token = generate_access_token(user.ID, user.Username, user.Role)
        
        # 데이터베이스 업데이트
        user.Access_Token = access_token
        db.commit()
        
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
def logout(refresh_token: str, db: Session = Depends(get_db)):
    try:
        user = db.query(Users).filter(Users.Refresh_Token == refresh_token).first()
        
        if user:
            # 토큰 정보 초기화
            user.Access_Token = None
            user.Refresh_Token = None
            user.Token_Expires_At = None
            db.commit()
        
        return {"success": True, "message": "로그아웃 완료"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그아웃 중 오류가 발생했습니다: {str(e)}")
