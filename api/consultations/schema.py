"""
    상담 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date, time, datetime

# 상담 저장 요청 스키마
class ConsultationCreateRequest(BaseModel):
    
    # 필수 필드들
    consultation_date: date = Field(..., description="상담 일자")
    start_time: time = Field(..., description="상담 시작 시간")
    end_time: time = Field(..., description="상담 종료 시간")
    customer_name: str = Field(..., max_length=50, description="고객명")
    chart_number: int = Field(..., description="차트번호")
    inflow_path: str = Field(..., max_length=50, description="유입경로 (여러 항목일 경우 , 구분)")
    consultation_type: str = Field(..., max_length=100, description="상담유형 (여러 항목일 경우 , 구분)")
    goal_treatment: bool = Field(..., description="목표시술 여부")
    concern_type: str = Field(..., max_length=255, description="고민유형 (여러 항목일 경우 , 구분)")
    is_upselling: bool = Field(..., description="업셀링 여부")
    consultation_content: str = Field(..., description="상담내용")
    
    # 선택 필드들
    purchased_items: Optional[str] = Field(None, max_length=255, description="구매상품 (여러 항목일 경우 , 구분)")
    has_membership: Optional[str] = Field(None, max_length=50, description="보유 맴버십")
    payment_type: Optional[str] = Field(None, max_length=50, description="결제타입")
    discount_rate: Optional[float] = Field(None, ge=0, le=10, description="추가할인율 (0~10%)")
    total_payment: Optional[int] = Field(None, ge=0, description="결제액 (원 단위)")

# 상담 저장 응답 스키마
class ConsultationCreateResponse(BaseModel):

    success: bool = Field(..., description="저장 성공 여부")
    message: str = Field(..., description="응답 메시지")


# 상담 조회 요청 스키마
class ConsultationReadRequest(BaseModel):
    """상담 조회 요청 스키마"""
    
    cursor: Optional[int] = Field(None, description="커서 ID (이전 조회의 마지막 ID)")
    limit: int = Field(30, ge=1, le=100, description="조회할 개수 (기본 30개, 최대 100개)")
    sort_by: Optional[Literal["id", "consultation_date", "customer_name", "created_at"]] = Field("id", description="정렬 기준 (id, consultation_date, customer_name, created_at)")
    sort_order: Optional[Literal["asc", "desc"]] = Field("desc", description="정렬 순서 (asc: 오름차순, desc: 내림차순)")

# 상담 조회 응답 스키마
class ConsultationReadResponse(BaseModel):
    """상담 조회 응답 스키마"""
    
    id: int = Field(..., description="상담 ID")
    consultation_date: Optional[date] = Field(None, description="상담 일자")
    start_time: Optional[datetime] = Field(None, description="상담 시작시간")
    end_time: Optional[datetime] = Field(None, description="상담 종료시간")
    customer_name: Optional[str] = Field(None, description="고객명")
    chart_number: Optional[int] = Field(None, description="차트번호")
    inflow_path: Optional[str] = Field(None, description="유입경로")
    consultation_type: Optional[str] = Field(None, description="상담유형")
    goal_treatment: Optional[bool] = Field(None, description="목표시술 여부")
    concern_type: Optional[str] = Field(None, description="고민유형")
    purchased_items: Optional[str] = Field(None, description="구매상품")
    is_upselling: Optional[bool] = Field(None, description="업셀링 여부")
    has_membership: Optional[str] = Field(None, description="보유 맴버십")
    payment_type: Optional[str] = Field(None, description="결제타입")
    consultation_content: Optional[str] = Field(None, description="상담내용")
    discount_rate: Optional[float] = Field(None, description="추가할인율")
    total_payment: Optional[int] = Field(None, description="결제액")
    created_at: Optional[datetime] = Field(None, description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")

class ConsultationListResponse(BaseModel):
    """상담 목록 조회 응답 스키마"""
    
    consultations: List[ConsultationReadResponse] = Field(..., description="상담 목록")
    next_cursor: Optional[int] = Field(None, description="다음 페이지 커서")
    has_next: bool = Field(..., description="다음 페이지 존재 여부")
    total_count: int = Field(..., description="전체 상담 수")