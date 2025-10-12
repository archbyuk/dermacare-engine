"""
    상담 생성 관련 서비스 로직
"""

from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException
from db.models.consultations import Consultations
from consultations.schema import ConsultationCreateRequest, ConsultationCreateResponse

# 상담 정보 저장
def create_consultation(db: Session, consultation_data: ConsultationCreateRequest) -> ConsultationCreateResponse:

    try:
        # 시작/종료 시간을 datetime으로 변환
        start_datetime = datetime.combine(consultation_data.consultation_date, consultation_data.start_time)
        end_datetime = datetime.combine(consultation_data.consultation_date, consultation_data.end_time)
        
        # 상담 시간 계산 (분 단위)
        duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
        
        # 상담 데이터 생성
        consultation = Consultations(
            consultation_date=consultation_data.consultation_date,
            start_time=start_datetime,
            end_time=end_datetime,
            customer_name=consultation_data.customer_name,
            chart_number=consultation_data.chart_number,
            inflow_path=consultation_data.inflow_path,
            consultation_type=consultation_data.consultation_type,
            goal_treatment=consultation_data.goal_treatment,
            concern_type=consultation_data.concern_type,
            purchased_items=consultation_data.purchased_items,
            is_upselling=consultation_data.is_upselling,
            has_membership=consultation_data.has_membership,
            payment_type=consultation_data.payment_type,
            consultation_content=consultation_data.consultation_content,
            discount_rate=consultation_data.discount_rate,
            total_payment=consultation_data.total_payment
        )
        
        # 데이터베이스에 저장
        db.add(consultation)
        db.commit()
        db.refresh(consultation)
        
        # 응답 데이터 생성
        return ConsultationCreateResponse(
            success=True,
            message=f"{consultation_data.consultation_date.strftime('%Y.%m.%d')}일자 총 {duration_minutes}분 {consultation_data.customer_name}({consultation_data.chart_number})고객님의 상담 내용이 저장되었습니다",
        )
        
    except Exception as e:
        db.rollback()
        
        raise HTTPException(
            status_code=500,
            detail=f"상담 정보 저장 중 오류가 발생했습니다: {str(e)}"
        )
