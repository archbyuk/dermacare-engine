from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from db.session import get_db
from auth.schema import RefreshRequest, LoginResponse
from auth.services.auth_service import process_token_refresh

router = APIRouter()

@router.post("/refresh", response_model=LoginResponse)
def refresh_token(
    request: RefreshRequest, 
    response: Response, 
    db: Session = Depends(get_db)
):
    try:
        # 토큰 갱신 처리 (서비스 레이어)
        user, access_token = process_token_refresh(db, request.refresh_token)
        
        # 새로운 액세스 토큰을 헤더에 설정
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=900,
            httponly=True,
            secure=True,
            samesite="strict",
            path="/"
        )
        
        return LoginResponse(
            success=True,
            message="토큰 갱신 성공",
            user_id=user.ID,
            role=user.Role,
            username=user.Username
        )
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"토큰 갱신 중 오류가 발생했습니다: {str(e)}")