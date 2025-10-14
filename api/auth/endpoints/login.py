from fastapi import HTTPException, Depends, Response, APIRouter
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from db.session import get_db
from db.models.users import Users
from auth.schema import LoginRequest, LoginResponse
from auth.utils.token_utils import generate_access_token, generate_refresh_token

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest, 
    response: Response, 
    db: Session = Depends(get_db)
):
    
    try:
        
        # 사용자 조회
        user = db.query(Users).filter(
            Users.Username == request.username
        ).first()
        
        
        if not user:
            raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
        
        # 비밀번호 확인 (간단한 문자열 비교): 추후 비밀번호 저장 방식 변경 필요 -> 비밀번호 암호화
        if user.Password != request.password:
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")
        
        
        # JWT 토큰 생성
        access_token = generate_access_token(user.ID, user.Username, user.Role)
        refresh_token = generate_refresh_token()
        
        # 리프레시 토큰 만료 시간 설정 (7일)
        refresh_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        # 데이터베이스에 토큰 정보 저장
        user.Refresh_Token = refresh_token
        user.Token_Expires_At = refresh_expires  # 리프레시 토큰 만료 시간 사용
        user.Last_Login_At = datetime.now(timezone.utc)
        
        # Set-Cookie 헤더 설정
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=900,        # 15분
            httponly=True,      # XSS 방지
            secure=True,       # 개발: False, 프로덕션: True
            samesite="strict",     # 크로스 오리진 허용 (개발 환경)
            path="/"
        )
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=7*24*3600,  # 7일
            httponly=True,
            secure=True,       # 개발: False, 프로덕션: True
            samesite="strict",     # 크로스 오리진 허용
            path="/"
        )
        
        db.commit()
        
        return LoginResponse(
            success=True,
            message="로그인 성공",
            user_id=user.ID,
            username=user.Username,
            role=user.Role
        )
        
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 중 오류가 발생했습니다: {str(e)}")