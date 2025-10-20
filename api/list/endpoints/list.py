"""
    [ '상품 전체 목록 조회' 엔드포인트 ]
    Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
"""

from fastapi import APIRouter, HTTPException
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..schema import ProductListResponse
from ..services.inquiry_service import inquiry_standard_products, inquiry_event_products

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

        > 데이터 read 속도 개선이 목표였는데 실패. (개선 x) >> Waiting for server response: 2.70s 여기서 병목이 걸림. 실제 데이터 처리는 0.4초 정도.

    3차 성능개선 (2025.10.16)
        - Product + Info JOIN 최적화: 쿼리 2회 → 1회 통합 (네트워크 왕복 1회 절감)
        - 직접 구현 방식으로 전환: 함수 호출 깊이 3단계 → 1단계 (복잡도 66% 감소)
        - 데드 코드 203줄 삭제: 529줄 → 326줄 (38% 코드 감소, 가독성 향상)
        - Standard/Event 동일 패턴 적용: 유지보수성 및 일관성 개선
        - 압축 설정 추가: Gzip 압축 설정 (600KB 이상 응답만 압축)
        
        > 결과: 쿼리 횟수 약 10% 감소, 응답 시간 약 25ms 단축, 코드 복잡도 대폭 개선

    프론트엔드 배포가 Vercel로 되어있는데, 서버 리전은 서울이고 버셀 리전은 미국(동부)임. 나중에 실사용량이 많아지면 리전 변경 필요.
    또한, 응답 데이터 크기가 너무 큼. 이건 추후에 최적화 필요.    
"""


@router.get("/products", response_model=ProductListResponse)
def get_products():

    try:
        products = []
        products_errors = []
        
        
        # Thread를 2개 생성하여 병렬 처리: Standard와 Event 상품을 동시에 조회
        with ThreadPoolExecutor(max_workers=2) as thread_executor:
            
            # 두 작업을 동시 실행: 각 작업은 별도 스레드에서 실행: thread_executor는 future를 반환함.
            thread_futures = {
                # 딕셔너리 형태로 생성하여, 각 future 작업 이름 저장
                thread_executor.submit(inquiry_standard_products): "standard",
                thread_executor.submit(inquiry_event_products): "event"
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
                
                # 에러가 없으면 결과를 리스트에 추가
                else:
                    products.extend(thread_future.result())
        
        # 총 상품 개수 조회: 두 작업의 결과를 합친 상품 개수
        total_count = len(products)
        
        # 문제: 전송 데이터 크기가 1.62MB로 너무 큼.. 
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

