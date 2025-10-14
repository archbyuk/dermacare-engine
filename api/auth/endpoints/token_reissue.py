from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from db.session import get_db
from db.models.users import Users
from auth.schema import RefreshRequest, LoginResponse
from auth.utils.token_utils import generate_access_token

router = APIRouter()

@router.post("/refresh", response_model=LoginResponse)
def refresh_token(
    request: RefreshRequest, 
    response: Response, 
    db: Session = Depends(get_db)
):
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
        
        # 새로운 액세스 토큰을 쿠키에 설정
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=900,   # 15분
            httponly=True,
            secure=True,
            samesite="strict"
        )
        
        return LoginResponse(
            success=True,
            message="토큰 갱신 성공",
            user_id=user.ID,
            role=user.Role,
            username=user.Username
        )
        
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"토큰 갱신 중 오류가 발생했습니다: {str(e)}")