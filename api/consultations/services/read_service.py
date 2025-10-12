"""
    상담 조회 관련 서비스 로직
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from fastapi import HTTPException
from db.models.consultations import Consultations
from consultations.schema import (
    ConsultationReadRequest,
    ConsultationListResponse,
    ConsultationReadResponse
)

# 상담 목록 조회
def get_consultations(db: Session, request: ConsultationReadRequest) -> ConsultationListResponse:

    try:
        # 기본 쿼리 설정
        query = db.query(Consultations)
        
        # 정렬 기준 필드 매핑
        sort_field_map = {
            "id": Consultations.id,
            "consultation_date": Consultations.consultation_date,
            "customer_name": Consultations.customer_name,
            "created_at": Consultations.created_at
        }
        
        # 정렬 필드 가져오기
        sort_field = sort_field_map.get(request.sort_by, Consultations.id)
        
        # 정렬 순서 결정
        order_func = desc if request.sort_order == "desc" else asc
        
        # 커서 기반 페이지네이션
        if request.cursor:
            if request.sort_order == "desc":
                query = query.filter(Consultations.id < request.cursor)
            else:
                query = query.filter(Consultations.id > request.cursor)
        
        # 정렬 및 제한
        consultations = query.order_by(order_func(sort_field), desc(Consultations.id)).limit(request.limit + 1).all()
        
        # 다음 페이지 존재 여부 확인
        has_next = len(consultations) > request.limit
        if has_next:
            consultations = consultations[:request.limit]
        
        # 다음 커서 설정
        next_cursor = consultations[-1].id if consultations and has_next else None
        
        # 전체 상담 수 조회
        total_count = db.query(Consultations).count()
        
        # 응답 데이터 변환
        consultation_responses = []
        for consultation in consultations:
            consultation_responses.append(ConsultationReadResponse(
                id=consultation.id,
                consultation_date=consultation.consultation_date,
                start_time=consultation.start_time,
                end_time=consultation.end_time,
                customer_name=consultation.customer_name,
                chart_number=consultation.chart_number,
                inflow_path=consultation.inflow_path,
                consultation_type=consultation.consultation_type,
                goal_treatment=consultation.goal_treatment,
                concern_type=consultation.concern_type,
                purchased_items=consultation.purchased_items,
                is_upselling=consultation.is_upselling,
                has_membership=consultation.has_membership,
                payment_type=consultation.payment_type,
                consultation_content=consultation.consultation_content,
                discount_rate=consultation.discount_rate,
                total_payment=consultation.total_payment,
                created_at=consultation.created_at,
                updated_at=consultation.updated_at
            ))
        
        return ConsultationListResponse(
            consultations=consultation_responses,
            next_cursor=next_cursor,
            has_next=has_next,
            total_count=total_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상담 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )
