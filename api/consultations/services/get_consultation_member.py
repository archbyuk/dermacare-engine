from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from consultations.schema import ConsultationMemberResponse
from fastapi import HTTPException

def consultation_member_load_process(db: Session, user_uuid: str) -> List[ConsultationMemberResponse]:
    """상담팀 사용자 목록 조회"""
    
    try:
        # 같은 조직 내의 모든 활성 사용자를 한 번의 쿼리로 조회
        get_members_query = """
            SELECT 
                DISTINCT member_user.uuid, member_user.display_name
            FROM 
                User AS `current_user`
            JOIN 
                Organization_User_Mapping AS current_user_oum 
                    ON `current_user`.id = current_user_oum.user_id
            JOIN 
                Organization_User_Mapping AS member_user_oum
                    ON `current_user_oum`.organization_id = `member_user_oum`.organization_id
            JOIN 
                User AS member_user
                    ON member_user.id = member_user_oum.user_id
            WHERE 
                `current_user`.uuid = :user_uuid
            AND 
                `current_user`.is_active = 1
            AND 
                current_user_oum.expired_at IS NULL
            AND 
                member_user.is_active = 1
            AND 
                member_user_oum.expired_at IS NULL
            ORDER BY 
                member_user.display_name ASC
        """
        
        # 쿼리 실행 후 결과 반환
        get_members_query_result = db.execute(
            text(get_members_query), {
                "user_uuid": user_uuid
            }
        ).fetchall()
        
        # 응답 데이터 변환 배열 생성
        consultation_members = []
        
        for member in get_members_query_result:
            consultation_members.append(
                ConsultationMemberResponse(
                    user_uuid=member.uuid,
                    display_name=member.display_name
                )
            )
        # member의 uuid와 display_name을 반환 → 또 다시 이 uuid로 상담 내역 조회 API에 파라미터로 활용
        
        return consultation_members
        
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상담 멤버 조회 중 오류가 발생했습니다: {str(e)}"
        )