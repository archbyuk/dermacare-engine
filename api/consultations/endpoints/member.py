from fastapi import APIRouter, Depends, HTTPException, Request
from security.permissions import require_permission
from db.session import get_db
from sqlalchemy.orm import Session
from consultations.schema import ConsultationMemberResponse
from consultations.services.get_consultation_member import consultation_member_load_process
from typing import List

member_router = APIRouter()

@member_router.get("/consultation-member", response_model=List[ConsultationMemberResponse])
@require_permission("consultation:read:all")
def get_consultation_member(
    request: Request,
    db: Session = Depends(get_db)
):
    """
        상담팀 팀원 목록 조회 API
        
        - 현재 사용자의 조직 내 모든 활성 사용자 조회
        - 프론트엔드에서 사용자 필터 드롭다운용
        - consultation:read:all 권한 필요
    """
    
    try:
        user_info = request.state.user
        user_uuid = user_info.get("user_uuid")
        
        if not user_uuid:
            raise HTTPException(
                status_code=401,
                detail="사용자 정보가 없습니다."
            )

        # user의 uuid를 통해 상담팀 팀원 목록 조회(팀장의 필터 기능을 위함)
        result = consultation_member_load_process(db, user_uuid)
        return result

    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상담 멤버 조회 중 예상치 못한 오류가 발생했습니다: {str(e)}"
        )