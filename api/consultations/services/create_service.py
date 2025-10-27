"""
    상담 생성 관련 서비스 로직
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import uuid
import json
from fastapi import HTTPException
from consultations.schema import ConsultationCreateRequest, ConsultationCreateResponse

# 상담 정보 저장
def create_consultation(db: Session, consultation_data: ConsultationCreateRequest, user_uuid: str) -> ConsultationCreateResponse:

    try:
        # 사용자 UUID로 사용자 ID와 조직 정보 조회
        user_query = """
            SELECT 
                u.id as user_id, oum.id as org_user_id, oum.organization_id
            FROM 
                User u
            JOIN 
                Organization_User_Mapping oum 
                    ON u.id = oum.user_id
            WHERE 
                u.uuid = :user_uuid
            AND 
                u.is_active = 1
            AND 
                oum.expired_at IS NULL
        """
        
        user_result = db.execute(text(user_query), {"user_uuid": user_uuid})
        user_row = user_result.fetchone()
        
        if not user_row:
            raise HTTPException(
                status_code=404,
                detail="사용자 정보를 찾을 수 없습니다."
            )
        
        user_id = user_row.user_id
        org_user_id = user_row.org_user_id
        organization_id = user_row.organization_id
        
        # 시작/종료 시간을 datetime으로 변환
        start_datetime = datetime.combine(consultation_data.consultation_date, consultation_data.start_time)
        end_datetime = datetime.combine(consultation_data.consultation_date, consultation_data.end_time)
        
        # 상담 시간 계산 (분 단위)
        duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
        
        # purchased_items를 JSON으로 변환
        purchased_items_json = None
        if consultation_data.purchased_items:
            # 쉼표로 구분된 문자열을 배열로 변환
            items_list = [item.strip() for item in consultation_data.purchased_items.split(',')]
            purchased_items_json = json.dumps(items_list, ensure_ascii=False)
        
        # 상담 데이터 삽입 쿼리
        consultation_uuid = str(uuid.uuid4())
        now = datetime.now()
        
        insert_query = """
            INSERT INTO Consultation (
                uuid, organization_id, org_user_id, is_active,
                consultation_date, start_time, end_time,
                customer_name, chart_number, inflow_path, consultation_type,
                goal_treatment, concern_type, purchased_items,
                is_upselling, has_membership, payment_type,
                consultation_content, discount_rate, total_payment,
                created_at, updated_at
            ) VALUES (
                :uuid, :organization_id, :org_user_id, 1,
                :consultation_date, :start_time, :end_time,
                :customer_name, :chart_number, :inflow_path, :consultation_type,
                :goal_treatment, :concern_type, :purchased_items,
                :is_upselling, :has_membership, :payment_type,
                :consultation_content, :discount_rate, :total_payment,
                :created_at, :updated_at
            )
        """
        
        # 쿼리 실행
        db.execute(text(insert_query), {
            'uuid': consultation_uuid,
            'organization_id': organization_id,
            'org_user_id': org_user_id,
            'consultation_date': consultation_data.consultation_date,
            'start_time': start_datetime,
            'end_time': end_datetime,
            'customer_name': consultation_data.customer_name,
            'chart_number': consultation_data.chart_number,
            'inflow_path': consultation_data.inflow_path,
            'consultation_type': consultation_data.consultation_type,
            'goal_treatment': consultation_data.goal_treatment,
            'concern_type': consultation_data.concern_type,
            'purchased_items': purchased_items_json,  # JSON으로 변환된 데이터
            'is_upselling': consultation_data.is_upselling,
            'has_membership': consultation_data.has_membership,
            'payment_type': consultation_data.payment_type,
            'consultation_content': consultation_data.consultation_content,
            'discount_rate': consultation_data.discount_rate,
            'total_payment': consultation_data.total_payment,
            'created_at': now,
            'updated_at': now
        })
        
        # 커밋
        db.commit()
        
        # 응답 데이터 생성
        return ConsultationCreateResponse(
            success=True,
            message=f"{consultation_data.consultation_date.strftime('%Y.%m.%d')}일자 총 {duration_minutes}분 {consultation_data.customer_name}({consultation_data.chart_number})고객님의 상담 내용이 저장되었습니다",
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        db.rollback()
        
        raise HTTPException(
            status_code=500,
            detail=f"상담 정보 저장 중 오류가 발생했습니다: {str(e)}"
        )
