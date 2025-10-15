from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from db.session import get_db
from auth.schema import LogoutRequest
from auth.services.auth_service import process_logout

router = APIRouter()

@router.post("/logout")
def logout(
    request: LogoutRequest, 
    response: Response, 
    db: Session = Depends(get_db)
):
    try:
        # 로그아웃 처리 (서비스 레이어)
        process_logout(db, request.refresh_token)
        
        # 쿠키 삭제 (엔드포인트 책임)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return {"success": True, "message": "로그아웃 완료"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그아웃 중 오류가 발생했습니다: {str(e)}")
