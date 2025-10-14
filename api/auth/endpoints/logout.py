from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.users import Users
from auth.schema import LogoutRequest

router = APIRouter()

@router.post("/logout")
def logout(
    request: LogoutRequest, 
    response: Response, 
    db: Session = Depends(get_db)
):
    try:
        user = db.query(Users).filter(
            Users.Refresh_Token == request.refresh_token
        ).first()
        
        if user:
            # 토큰 정보 초기화
            user.Refresh_Token = None
            user.Token_Expires_At = None
            
            db.commit()
        
        # 쿠키 삭제
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return {"success": True, "message": "로그아웃 완료"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그아웃 중 오류가 발생했습니다: {str(e)}")
