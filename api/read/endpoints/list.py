"""
    [ '상품 전체 목록 조회' 엔드포인트 ]
    Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from concurrent.futures import ThreadPoolExecutor, as_completed
from db.session import SessionLocal
from db.models.product import ProductEvent, ProductStandard
from ..schema import ProductListResponse
from ..services.list_service import build_standard_products_optimized, build_event_products_optimized
import time


router = APIRouter()


"""
    상품 전체 목록 조회:
        
        Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
        프론트엔드에서 상품 목록을 띄우기 위한 API입니다.

    1차 성능개선(2025.09.24): 로딩 시간 4~5초 > 평균 3s로 감소
        1. N+1 쿼리 문제 해결
        2. 최적화된 데이터 구조 사용

    2차 성능개선(2025.10.15)
        - 쓸모없는 페이지네이션 params 제거
        - product_type 분기 제거 (항상 all로 들어옴)
        - 병렬 처리 도입 (ThreadPoolExecutor)
        - Standard와 Event 상품을 동시 조회 및 처리

        > 데이터 read 속도 개선이 목표였는데 실패. (개선 x)

    3차 성능개선 ()
        - 에러 처리 개선 예정
        - 코드 베이스 정리 및 유지보수성 개선 예정
        - 쿼리 최적화 예정
"""


def fetch_standard_products():
    """Standard 상품 조회 및 처리 (별도 세션 사용)"""
    start_time = time.time()
    db = SessionLocal()
    
    try:
        query_start = time.time()
        standard_products = db.query(ProductStandard).order_by(
            desc(ProductStandard.Standard_Start_Date)
        ).all()
        query_time = time.time() - query_start
        
        build_start = time.time()
        result = build_standard_products_optimized(standard_products, db)
        build_time = time.time() - build_start
        
        total_time = time.time() - start_time
        print(f"[PERF] Standard - 쿼리: {query_time:.3f}s | 가공: {build_time:.3f}s | 총: {total_time:.3f}s")
        
        return result
    
    finally:
        db.close()


def fetch_event_products():
    """Event 상품 조회 및 처리 (별도 세션 사용)"""
    start_time = time.time()
    db = SessionLocal()
    
    try:
        query_start = time.time()
        event_products = db.query(ProductEvent).order_by(
            desc(ProductEvent.Event_Start_Date)
        ).all()
        query_time = time.time() - query_start
        
        build_start = time.time()
        result = build_event_products_optimized(event_products, db)
        build_time = time.time() - build_start
        
        total_time = time.time() - start_time
        print(f"[PERF] Event - 쿼리: {query_time:.3f}s | 가공: {build_time:.3f}s | 총: {total_time:.3f}s")
        
        return result
    
    finally:
        db.close()


@router.get("/products", response_model=ProductListResponse)
def get_products():
    api_start = time.time()
    
    try:
        products = []
        products_errors = []
        
        parallel_start = time.time()
        print(f"\n{'='*60}")
        print(f"[PERF] API 시작 - 병렬 처리 시작")
        
        # Thread를 2개 생성하여 병렬 처리: Standard와 Event 상품을 동시에 조회
        with ThreadPoolExecutor(max_workers=2) as thread_executor:
            
            # 두 작업을 동시 실행: 각 작업은 별도 스레드에서 실행: thread_executor는 future를 반환함.
            thread_futures = {
                # 딕셔너리 형태로 생성하여, 각 future 작업 이름 저장
                thread_executor.submit(fetch_standard_products): "standard",
                thread_executor.submit(fetch_event_products): "event"
            }

            # 여기서 두 작업 중 하나라도 에러나면, 실패한 작업 에러 메시지를 반환하고 에러 리스트에 추가해서 처리해야 함.
            for thread_future in as_completed(thread_futures):
                # as_completed는 완료된 future를 순차적으로 반환함.(성공이나 실패나 상관없이 순차적으로 반환)
                
                # 각 future의 작업 이름 가져오기: standard 또는 event
                task_name = thread_futures[thread_future]
                error = thread_future.exception()
                
                # 에러가 있으면 에러 리스트에 추가하고
                if error:
                    products_errors.append(f"{task_name}: {error}")
                    print(f"{task_name}: {error}")
                
                # 에러가 없으면 결과를 리스트에 추가
                else:
                    products.extend(thread_future.result())
        
        parallel_time = time.time() - parallel_start
        print(f"[PERF] 병렬 처리 완료: {parallel_time:.3f}s")
        
        # 총 상품 개수 조회: 두 작업의 결과를 합친 상품 개수
        total_count = len(products)
        
        api_total_time = time.time() - api_start
        print(f"[PERF] API 전체 응답 시간: {api_total_time:.3f}s")
        print(f"{'='*60}\n")
        
        return ProductListResponse(
            status="success",
            message="상품 전체 목록 조회 완료",
            errors=products_errors,
            data=products,
            total_count=total_count
        )
        
    except HTTPException:
        raise
   
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상품 목록 조회 중 오류 발생: {str(e)}"
        )

