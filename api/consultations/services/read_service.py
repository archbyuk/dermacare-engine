from time import timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from datetime import datetime, time, timedelta, timezone
from fastapi import HTTPException
from consultations.schema import ConsultationReadRequest, ConsultationListResponse, ConsultationReadResponse

# 상담일자 필터 조건 생성 헬퍼 함수: 날짜 조건은 재기획 필요
def _build_date_filter_condition(filter_type: str, filter_value: str):
    """상담일자 필터 조건과 파라미터 생성"""
    from datetime import datetime, timedelta
    
    if filter_type == "day":
        # 하루: 특정 날짜
        return "c.consultation_date = :consultation_date", {"consultation_date": filter_value}
    
    elif filter_type == "week":
        # 일주일: 해당 주의 월요일~일요일
        try:
            target_date = datetime.strptime(filter_value, "%Y-%m-%d").date()
            monday = target_date - timedelta(days=target_date.weekday())
            sunday = monday + timedelta(days=6)
            return "c.consultation_date BETWEEN :start_date AND :end_date", {
                "start_date": monday.strftime("%Y-%m-%d"),
                "end_date": sunday.strftime("%Y-%m-%d")
            }
        except ValueError:
            return None, {}
    
    elif filter_type == "month":
        # 한 달: 해당 월의 모든 날
        return "c.consultation_date LIKE :month_pattern", {"month_pattern": f"{filter_value}%"}
    
    return None, {}

# 상담 목록 조회
def get_all_consultations(
    db: Session, 
    request: ConsultationReadRequest, 
    organization_uuid: str
) -> ConsultationListResponse:

    try:

        # 기본 쿼리: 상담 목록 조회 쿼리 (조직 필터링 포함, 윈도우 함수로 전체 개수 포함)
        # COUNT는 LIMIT 전에 실행되므로, 조회 가능한 전체 갯수가 나옴.
        base_query = """
            SELECT
                c.*, COUNT(*) OVER() as total_count
            FROM 
                Consultation AS c
            JOIN
                Organization_User_Mapping AS org_user_map 
                    ON c.org_user_id = org_user_map.id
            JOIN 
                User AS user_creator
                    ON org_user_map.user_id = user_creator.id
            JOIN 
                Organization AS org
                    ON org_user_map.organization_id = org.id
            LEFT JOIN 
                Organization_User_Mapping AS org_user_filter 
                    ON c.org_user_id = org_user_filter.id
            LEFT JOIN
                User AS user_filter 
                    ON org_user_filter.user_id = user_filter.id
            WHERE 
                c.is_active = 1
        """
        
        # sort_direction이 정수인 경우 문자열로 변환
        sort_direction_str = str(request.sort_direction.value).upper()
        order_by_query = f"c.{request.sort_by.value} {sort_direction_str}"
        
        # 페이지네이션 조건
        page_condition = f"LIMIT {request.page_size} OFFSET {(request.page - 1) * request.page_size}"
        
        
        # 필터 조건들을 동적으로 추가
        filter_conditions = []
        filter_params = {}

        # 유입경로 필터
        if request.inflow_path:
            filter_conditions.append("c.inflow_path = :inflow_path")
            filter_params["inflow_path"] = request.inflow_path.value
            
        # 상담유형 필터
        if request.consultation_type:
            filter_conditions.append("c.consultation_type = :consultation_type")
            filter_params["consultation_type"] = request.consultation_type.value
        
        # 고민유형 필터
        if request.concern_type:
            filter_conditions.append("c.concern_type = :concern_type")
            filter_params["concern_type"] = request.concern_type.value
        
        # 목표시술 필터
        if request.goal_treatment:
            filter_conditions.append("c.goal_treatment = :goal_treatment")
            filter_params["goal_treatment"] = request.goal_treatment.value == 1
        
        
        # 조직 필터링 - 요청받은 조직 uuid에 해당하는 상담내역만 조회
        filter_conditions.append("org.uuid = :organization_uuid")
        filter_params["organization_uuid"] = organization_uuid
        # 상담자 필터
        if request.consultant_uuid:
            filter_conditions.append("user_filter.uuid = :consultant_uuid")
            filter_params["consultant_uuid"] = request.consultant_uuid
        
        # 상담일자 필터: 재기획
        if request.consultation_date_filter_type and request.consultation_date_filter_value:
            date_condition, date_params = _build_date_filter_condition(
                request.consultation_date_filter_type.value, 
                request.consultation_date_filter_value
            )

            if date_condition:
                filter_conditions.append(date_condition)
                filter_params.update(date_params)
        

        # 필터 조건을 쿼리에 추가: and 조건으로 추가
        if filter_conditions:
            base_query += " AND " + " AND ".join(filter_conditions)
        
        # 최종 쿼리 구성
        final_query = f"""
            {base_query}
            ORDER BY {order_by_query}
            {page_condition}
        """
        
        # 쿼리 실행 (윈도우 함수로 전체 개수 포함)
        result = db.execute(
            text(final_query), filter_params
        )
        
        # 쿼리 실행 결과 가져오기
        consultations = result.fetchall()
        
        # 전체 개수 추출 (첫 번째 행에서 가져옴)
        total_count = consultations[0].total_count if consultations else 0
    
        # 한국 시간대로 변환
        kst = timezone(timedelta(hours=9))
        
        # 응답 데이터 변환
        consultation_responses = []
        
        for consultation in consultations:
            # purchased_items JSON을 문자열로 변환
            purchased_items_str = None
            
            if consultation.purchased_items:
                try:
                    # JSON 문자열을 파싱해서 쉼표로 구분된 문자열로 변환
                    items_list = json.loads(consultation.purchased_items)
                    purchased_items_str = ', '.join(items_list)
                
                except (json.JSONDecodeError, TypeError):
                    purchased_items_str = consultation.purchased_items
            
            # 응답 데이터 추가, 타입: ConsultationReadResponse
            consultation_responses.append(
                ConsultationReadResponse(
                    # id=consultation.id,
                    consultation_date=consultation.consultation_date,
                    start_time=consultation.start_time.astimezone(kst).time(),
                    end_time=consultation.end_time.astimezone(kst).time(),
                    customer_name=consultation.customer_name,
                    chart_number=consultation.chart_number,
                    inflow_path=consultation.inflow_path,
                    consultation_type=consultation.consultation_type,
                    goal_treatment=consultation.goal_treatment,
                    concern_type=consultation.concern_type,
                    purchased_items=purchased_items_str,
                    is_upselling=consultation.is_upselling,
                    has_membership=consultation.has_membership,
                    payment_type=consultation.payment_type,
                    consultation_content=consultation.consultation_content,
                    discount_rate=consultation.discount_rate,
                    total_payment=consultation.total_payment,
                    created_at=consultation.created_at,
                    updated_at=consultation.updated_at
                )
            )
        
        # 페이지네이션 메타데이터 계산
        total_pages = (total_count + request.page_size - 1) // request.page_size
        has_next = request.page < total_pages
        has_previous = request.page > 1
        
        return ConsultationListResponse(
            consultations=consultation_responses,
            current_page=request.page,
            total_pages=total_pages,
            total_items=total_count,
            has_next=has_next,
            has_previous=has_previous
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상담 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

# 자신의 상담 목록 조회
def get_my_consultations(
    db: Session, 
    request: ConsultationReadRequest, 
    user_uuid: str, 
    organization_uuid: str
) -> ConsultationListResponse:

    try:
        
        # 기본 쿼리: 자신의 상담만 조회 (조직 필터링 포함, 윈도우 함수로 전체 개수 포함)
        base_query = """
            SELECT 
                c.*,
                COUNT(*) OVER() as total_count
            FROM 
                Consultation AS c
            LEFT JOIN Organization_User_Mapping org_user ON c.org_user_id = org_user.id
            LEFT JOIN User user_filter ON org_user.user_id = user_filter.id
            LEFT JOIN Organization org ON org_user.organization_id = org.id
            WHERE 
                c.is_active = 1
                AND user_filter.uuid = :user_uuid
                AND org.uuid = :organization_uuid
        """

        # 정렬 필드 결정 (전체 목록과 동일한 로직)
        sort_direction_str = str(request.sort_direction.value).upper()
        order_by_query = f"c.{request.sort_by.value} {sort_direction_str}"

        # 페이지네이션 조건
        page_condition = f"LIMIT {request.page_size} OFFSET {(request.page - 1) * request.page_size}"
        

        # 필터 조건들을 동적으로 추가
        filter_conditions = []
        filter_params = {
            "user_uuid": user_uuid,
            "organization_uuid": organization_uuid
        }
        
        # 유입경로 필터
        if request.inflow_path:
            filter_conditions.append("c.inflow_path = :inflow_path")
            filter_params["inflow_path"] = request.inflow_path.value
        
        # 상담유형 필터
        if request.consultation_type:
            filter_conditions.append("c.consultation_type = :consultation_type")
            filter_params["consultation_type"] = request.consultation_type.value
        
        # 고민유형 필터
        if request.concern_type:
            filter_conditions.append("c.concern_type = :concern_type")
            filter_params["concern_type"] = request.concern_type.value
        
        # 목표시술 필터
        if request.goal_treatment:
            filter_conditions.append("c.goal_treatment = :goal_treatment")
            filter_params["goal_treatment"] = request.goal_treatment.value == "true"
        
        # 상담일자 필터
        if request.consultation_date_filter_type and request.consultation_date_filter_value:
            date_condition, date_params = _build_date_filter_condition(
                request.consultation_date_filter_type.value, 
                request.consultation_date_filter_value
            )
            if date_condition:
                filter_conditions.append(date_condition)
                filter_params.update(date_params)
        
        # 필터 조건을 쿼리에 추가
        if filter_conditions:
            base_query += " AND " + " AND ".join(filter_conditions)
        
        # 최종 쿼리 구성
        final_query = f"""
            {base_query}
            ORDER BY {order_by_query}
            {page_condition}
        """
        
        result = db.execute(
            text(final_query), filter_params
        )

        # 쿼리 실행 결과 가져오기
        consultations = result.fetchall()

        kst = timezone(timedelta(hours=9))
        
        # 전체 개수 추출 (첫 번째 행에서 가져옴)
        total_count = consultations[0].total_count if consultations else 0
        
        # 응답 데이터 변환
        consultation_responses = []
        
        for consultation in consultations:
            # purchased_items JSON을 문자열로 변환
            purchased_items_str = None
            
            if consultation.purchased_items:
                try:
                    # JSON 문자열을 파싱해서 쉼표로 구분된 문자열로 변환
                    items_list = json.loads(consultation.purchased_items)
                    purchased_items_str = ', '.join(items_list)
                
                except (json.JSONDecodeError, TypeError):
                    # JSON 파싱 실패 시 원본 문자열 사용
                    purchased_items_str = consultation.purchased_items
            
            consultation_responses.append(ConsultationReadResponse(
                id=consultation.id,
                consultation_date=consultation.consultation_date,
                start_time=consultation.start_time.astimezone(kst).time(),
                end_time=consultation.end_time.astimezone(kst).time(),
                customer_name=consultation.customer_name,
                chart_number=consultation.chart_number,
                inflow_path=consultation.inflow_path,
                consultation_type=consultation.consultation_type,
                goal_treatment=consultation.goal_treatment,
                concern_type=consultation.concern_type,
                purchased_items=purchased_items_str,  # 변환된 문자열
                is_upselling=consultation.is_upselling,
                has_membership=consultation.has_membership,
                payment_type=consultation.payment_type,
                consultation_content=consultation.consultation_content,
                discount_rate=consultation.discount_rate,
                total_payment=consultation.total_payment,
                created_at=consultation.created_at,
                updated_at=consultation.updated_at
            ))
        
        # 페이지네이션 메타데이터 계산
        total_pages = (total_count + request.page_size - 1) // request.page_size
        has_next = request.page < total_pages
        has_previous = request.page > 1
        
        return ConsultationListResponse(
            consultations=consultation_responses,
            current_page=request.page,
            total_pages=total_pages,
            total_items=total_count,
            has_next=has_next,
            has_previous=has_previous
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"자신의 상담 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )
