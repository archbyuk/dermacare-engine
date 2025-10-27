from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from consultations.schema import (
    ConsultationReadRequest,
    ConsultationListResponse,
    InflowPath,
    ConsultationType,
    ConcernType,
    GoalTreatment,
    SortBy,
    SortDirection,
    DateFilterType
)
from consultations.services.read_service import get_all_consultations, get_my_consultations
from security.permissions import require_permission

# 라우터 생성
read_router = APIRouter()

# 모든 상담 목록 조회 API (팀장용)
@read_router.get("/all-consultations", response_model=ConsultationListResponse)
@require_permission("consultation:read:all")
def get_all_consultations_endpoint(
    
    # 요청 데이터
    request: Request,
    
    # 조직 정보
    organization_uuid: str = Query(..., description="조직 uuid (필수)"),
    
    # 페이지네이션 설정
    page: int = Query(1, ge=1, description="페이지 번호 (기본 1페이지)"),
    page_size: int = Query(5, ge=1, description="페이지 당 20개의 상담 데이터 조회"),
    
    # 필터 설정
    inflow_path: Optional[InflowPath] = Query(None, description="유입경로 필터"),
    consultation_type: Optional[ConsultationType] = Query(None, description="상담유형 필터"),
    concern_type: Optional[ConcernType] = Query(None, description="고민유형 필터"),
    goal_treatment: Optional[GoalTreatment] = Query(None, description="목표시술 필터"),
    consultant_uuid: Optional[str] = Query(None, description="상담자 필터"),
    consultation_date_filter_type: Optional[DateFilterType] = Query(None, description="상담일자 필터 타입"),
    consultation_date_filter_value: Optional[str] = Query(None, description="상담일자 필터 값"),
    
    # 정렬 설정
    sort_by: SortBy = Query(SortBy.CREATED_AT, description="정렬 기준"),
    sort_direction: SortDirection = Query(SortDirection.DESC, description="정렬 방향"),
    
    # db 세션
    db: Session = Depends(get_db)
):

    try:
        # 사용자 정보 추출 (조직별 필터링용)
        user_info = request.state.user

        if not user_info:
            raise HTTPException(
                status_code=401, 
                detail="존재하지 않는 사용자입니다."
            )
        

        # 조직 권한 검증
        user_org_uuids = [org["organization_uuid"] for org in user_info["organizations"]]
        
        if organization_uuid not in user_org_uuids:
            raise HTTPException(status_code=403, detail="해당 조직에 대한 권한이 없습니다.")
        

        # 요청 데이터 생성
        request_data = ConsultationReadRequest(
            page=page,
            page_size=page_size,

            inflow_path=inflow_path,
            consultation_type=consultation_type,
            concern_type=concern_type,
            goal_treatment=goal_treatment,
            consultant_uuid=consultant_uuid,
            consultation_date_filter_type=consultation_date_filter_type,
            consultation_date_filter_value=consultation_date_filter_value,
            
            sort_by=sort_by,
            sort_direction=sort_direction
        )
        
        result = get_all_consultations(db, request_data, organization_uuid)
        
        return result
        
    except HTTPException:
        raise
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상담 조회 중 예상치 못한 오류가 발생했습니다: {str(e)}"
        )




# 자신의 상담 목록 조회 API (일반 사용자용)
@read_router.get("/own-consultations", response_model=ConsultationListResponse)
@require_permission("consultation:read:own")
def get_own_consultations(
    request: Request,
    organization_uuid: str = Query(..., description="조직 UUID (필수)"),
    page: int = Query(1, ge=1, description="페이지 번호 (기본 1페이지)"),
    page_size: int = Query(20, ge=1, description="페이지 당 20개의 상담 데이터 조회"),
    inflow_path: Optional[InflowPath] = Query(None, description="유입경로 필터"),
    consultation_type: Optional[ConsultationType] = Query(None, description="상담유형 필터"),
    concern_type: Optional[ConcernType] = Query(None, description="고민유형 필터"),
    goal_treatment: Optional[GoalTreatment] = Query(None, description="목표시술 필터"),
    consultation_date_filter_type: Optional[DateFilterType] = Query(None, description="상담일자 필터 타입 (day, week, month)"),
    consultation_date_filter_value: Optional[str] = Query(None, description="상담일자 필터 값"),
    sort_by: SortBy = Query(SortBy.CREATED_AT, description="정렬 기준 (created_at: 등록 날짜, total_payment: 총 결재액)"),
    sort_direction: SortDirection = Query(SortDirection.DESC, description="정렬 방향 (asc: 오름차순, desc: 내림차순)"),
    db: Session = Depends(get_db)
):
    try:
        # 사용자 정보 추출 (자신의 상담만 조회용)
        user_info = request.state.user
        user_uuid = user_info.get("user_uuid")
        
        # 조직 권한 검증
        user_org_uuids = [org["organization_uuid"] for org in user_info["organizations"]]
        
        # 조직 uuid가 사용자의 소속 조직에 포함되어 있지 않으면 권한 없음 예외 발생
        if organization_uuid not in user_org_uuids:
            raise HTTPException(status_code=403, detail="해당 조직에 대한 권한이 없습니다.")
        
        # 요청 데이터 생성
        request_data = ConsultationReadRequest(
            page=page,
            page_size=page_size,
            inflow_path=inflow_path,
            consultation_type=consultation_type,
            concern_type=concern_type,
            goal_treatment=goal_treatment,
            consultation_date_filter_type=consultation_date_filter_type,
            consultation_date_filter_value=consultation_date_filter_value,
            sort_by=sort_by,
            sort_direction=sort_direction
        )
        
        result = get_my_consultations(db, request_data, user_uuid, organization_uuid)
        return result
        
    except HTTPException:
        raise
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상담 조회 중 예상치 못한 오류가 발생했습니다: {str(e)}"
        )
