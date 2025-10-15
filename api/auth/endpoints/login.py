from fastapi import HTTPException, Depends, Response, APIRouter
from sqlalchemy.orm import Session
from db.session import get_db
from auth.schema import LoginRequest, LoginResponse
from auth.services.auth_service import process_login

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest, 
    response: Response, 
    db: Session = Depends(get_db)
):
    try:
        # 로그인 처리 (서비스 레이어)
        user, access_token, refresh_token = process_login(db, request.username, request.password)
        
        # Set-Cookie 헤더 설정 (엔드포인트 책임)
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=900,            # 15분
            httponly=True,          # XSS 방지
            secure=True,            # HTTPS 사용
            samesite="strict",      # 크로스 오리진 방지
            path="/"                # 쿠키 경로(root: 전역 허용)
        )
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=7*24*3600,      # 7일
            httponly=True,          # XSS 방지
            secure=True,            # HTTPS 사용
            samesite="strict",      # 크로스 오리진 방지
            path="/"                # 쿠키 경로(root: 전역 허용)
        )
        
        return LoginResponse(
            success=True,
            message="로그인 성공",    # 성공 메시지 개선 필요: {user.team}의 {user.Username}님 환영합니다.
            user_id=user.ID,
            username=user.Username,
            role=user.Role
        )
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 중 오류가 발생했습니다: {str(e)}")