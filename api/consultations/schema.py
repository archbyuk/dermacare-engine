from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date, time, datetime
from enum import Enum

# Enum 정의
class InflowPath(str, Enum):
    PROMOTION = "판촉물"
    WALK_IN = "워크인"
    REFERRAL = "지인 소개"
    DB_MARKETING = "DB 마케팅"
    GOOGLE_SEARCH = "구글 검색"
    LOCAL_MARKETING = "로컬 마케팅"
    NAVER_SEARCH = "네이버 검색"
    NAVER_CAFE = "네이버 카페"

class ConsultationType(str, Enum):
    NEW_PATIENT = "신환상담"
    FOLLOW_UP = "경과상담"
    DISCHARGE = "종료상담"
    RE_VISIT = "재방상담"

class ConcernType(str, Enum):
    FILLER = "필러"
    HAIR_REMOVAL = "제모"
    WEDDING = "결혼"
    LIFTING = "리프팅"
    MOLE_REMOVAL = "점제거"
    BOTOX = "보톡스"
    PIGMENT_TREATMENT = "색소치료"
    SKIN_CARE = "피부관리"
    THREAD_LIFTING = "실리프팅"
    BASIC_CONSULTATION = "기본상담"
    SKIN_BOOST = "스킨부스트"

class GoalTreatment(str, Enum):
    YES = "true"
    NO = "false"

class SortBy(str, Enum):
    CREATED_AT = "created_at"
    TOTAL_PAYMENT = "total_payment"

class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"

class DateFilterType(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"

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
    
    # 페이지네이션 설정
    page: int = Field(1, ge=1, description="페이지 번호 (기본 1페이지)")
    page_size: int = Field(5, ge=1, description="페이지 당 20개의 상담 데이터 조회")
    
    # 필터 설정: 상담 날짜, 유입경로, 상담 유형(환자 분류), 고민 유형, 목표 시술, 상담자(개별, all)
    inflow_path: Optional[InflowPath] = Field(None, description="유입경로 필터")
    consultation_type: Optional[ConsultationType] = Field(None, description="상담유형(환자 분류) 필터")
    concern_type: Optional[ConcernType] = Field(None, description="고민유형 필터")
    goal_treatment: Optional[GoalTreatment] = Field(None, description="목표시술 필터")
    consultant_uuid: Optional[str] = Field(None, description="상담자 UUID 필터 (특정 팀원의 상담만 조회)")
    # 상담일자 필터 타입: day, week, month: 수정 예정
    consultation_date_filter_type: Optional[DateFilterType] = Field(None, description="상담일자 필터 타입 (day: 하루, week: 일주일, month: 한 달)")
    # 상담일자 필터 값: 2025-10-27, 2025-10-27, 2025-10: 수정 예정
    consultation_date_filter_value: Optional[str] = Field(None, description="상담일자 필터 값 (day: 2025-10-27, week: 2025-10-27, month: 2025-10)")
    
    # 정렬 설정
    sort_by: Optional[SortBy] = Field(SortBy.CREATED_AT, description="정렬 기준 (created_at: 등록 날짜, total_payment: 총 결재액)")
    
    # 정렬 방향 설정
    sort_direction: Optional[SortDirection] = Field(SortDirection.DESC, description="정렬 방향 (asc: 오름차순, desc: 내림차순)")
    

# 상담 멤버 조회 응답 스키마
class ConsultationMemberResponse(BaseModel):
    """상담 멤버 조회 응답 스키마"""
    
    user_uuid: str = Field(..., description="사용자 UUID")
    display_name: str = Field(..., description="사용자 표시명")

# 상담 조회 응답 스키마
class ConsultationReadResponse(BaseModel):
    """상담 조회 응답 스키마"""
    
    # id: int = Field(..., description="상담 ID")
    consultation_date: Optional[date] = Field(None, description="상담 일자")
    start_time: Optional[time] = Field(None, description="상담 시작시간")
    end_time: Optional[time] = Field(None, description="상담 종료시간")
    customer_name: Optional[str] = Field(None, description="고객명")
    chart_number: Optional[str] = Field(None, description="차트번호")
    inflow_path: Optional[str] = Field(None, description="유입경로")
    consultation_type: Optional[str] = Field(None, description="상담유형")
    goal_treatment: Optional[bool] = Field(None, description="목표시술")
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
    current_page: int = Field(..., description="현재 페이지 번호")
    total_pages: int = Field(..., description="전체 페이지 수")
    total_items: int = Field(..., description="전체 데이터 수")
    has_next: bool = Field(..., description="다음 페이지 존재 여부")
    has_previous: bool = Field(..., description="이전 페이지 존재 여부")