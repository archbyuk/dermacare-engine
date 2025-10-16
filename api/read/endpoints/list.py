"""
    [ '상품 전체 목록 조회' 엔드포인트 ]
    Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import desc
from concurrent.futures import ThreadPoolExecutor, as_completed
from db.session import SessionLocal
from db.models.product import ProductEvent, ProductStandard
from db.models.info import InfoStandard, InfoEvent
from ..schema import ProductListResponse
from ..services.list_service import process_procedure_data

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
        
        > 결과: 쿼리 횟수 약 10% 감소, 응답 시간 약 25ms 단축, 코드 복잡도 대폭 개선
"""


def inquiry_standard_products():
    """Standard 상품 조회 및 처리 (JOIN 최적화 + Dict 반환 방식)"""
    db = SessionLocal()
    
    try:
        
        # 1. JOIN으로 Product + Info 동시 조회
        standard_query_results = db.query(
            ProductStandard, InfoStandard
        ).outerjoin(
            InfoStandard,
            ProductStandard.Standard_Info_ID == InfoStandard.ID
        ).order_by(
            desc(ProductStandard.Standard_Start_Date)
        ).all()
        
        
        # 최종 응답용 리스트
        standard_products_list = []

        # Procedure 데이터를 가져오기 ProductStandard 테이블의 데이터만 가져오기
        query_results_standard_product = []
        
        # Procedure 데이터를 가져오기 위한 ID 수집
        element_ids, bundle_ids, custom_ids, sequence_ids = [], [], [], []
        
        # 기본 정보 구성 + ID 수집
        for standard_product, standard_info in standard_query_results:
            
            # for문이 돌 때마다 순차적으로 리스트에 추가
            query_results_standard_product.append(standard_product)
            
            # Procedure ID 수집
            if standard_product.Element_ID:
                element_ids.append(standard_product.Element_ID)
            
            elif standard_product.Bundle_ID:
                bundle_ids.append(standard_product.Bundle_ID)
            
            elif standard_product.Custom_ID:
                custom_ids.append(standard_product.Custom_ID)
            
            elif standard_product.Sequence_ID:
                sequence_ids.append(standard_product.Sequence_ID)
            
            # 기본 정보만 구성 (procedure_names, class_types 없음!)
            standard_product_data = {
                "ID": standard_product.ID,
                "Product_Type": "standard",
                "Package_Type": standard_product.Package_Type,
                "Sell_Price": standard_product.Sell_Price,
                "Original_Price": standard_product.Original_Price,
                "Product_Name": standard_info.Product_Standard_Name if standard_info else f"Standard {standard_product.ID}",
                "Product_Description": standard_info.Product_Standard_Description if standard_info else f"Description {standard_product.ID}",
                "Precautions": standard_info.Precautions if standard_info else f"Precautions {standard_product.ID}"
            }
            
            standard_products_list.append(standard_product_data)

        # 자, 이제 여기서 1차 응답 완성이고, element~sequence 데이터를 가져오기 위한 ids 배열도 준비가 된 상황.
        
        # Procedure 데이터 조회 및 추가
        if element_ids or bundle_ids or custom_ids or sequence_ids:
            procedure_dict = process_procedure_data(
                db,
                query_results_standard_product,
                element_ids,
                bundle_ids,
                custom_ids,
                sequence_ids
            )
            # procedure_dict: {30030: {"procedure_names": [...], "class_types": [...]}, ...}
            
            # 5. Procedure 정보를 각 상품에 추가 (한 번에 merge)
            for product in standard_products_list:
                product.update(
                    procedure_dict.get(product["ID"], {
                        "procedure_names": [],
                        "class_types": []
                    })
                )
        else:
            # Procedure가 없는 경우 빈 배열 추가
            for product in standard_products_list:
                product.update({
                    "procedure_names": [],
                    "class_types": []
                })
        
        # 6. 최종 응답 반환
        return standard_products_list
    
    finally:
        db.close()


def inquiry_event_products():
    """Event 상품 조회 및 처리 (JOIN 최적화 + Dict 반환 방식)"""
    db = SessionLocal()
    
    try:
        
        # 1. JOIN으로 Product + Info 동시 조회
        event_query_results = db.query(
            ProductEvent, InfoEvent
        ).outerjoin(
            InfoEvent,
            ProductEvent.Event_Info_ID == InfoEvent.ID
        ).order_by(
            desc(ProductEvent.Event_Start_Date)
        ).all()
        
        
        # 최종 응답용 리스트
        event_products_list = []

        # Procedure 데이터를 가져오기 ProductEvent 테이블의 데이터만 가져오기
        query_results_event_product = []
        
        # Procedure 데이터를 가져오기 위한 ID 수집
        element_ids, bundle_ids, custom_ids, sequence_ids = [], [], [], []
        
        # 기본 정보 구성 + ID 수집
        for event_product, event_info in event_query_results:
            
            # for문이 돌 때마다 순차적으로 리스트에 추가
            query_results_event_product.append(event_product)
            
            # Procedure ID 수집
            if event_product.Element_ID:
                element_ids.append(event_product.Element_ID)
            
            elif event_product.Bundle_ID:
                bundle_ids.append(event_product.Bundle_ID)
            
            elif event_product.Custom_ID:
                custom_ids.append(event_product.Custom_ID)
            
            elif event_product.Sequence_ID:
                sequence_ids.append(event_product.Sequence_ID)
            
            # 기본 정보만 구성 (procedure_names, class_types 없음!)
            event_product_data = {
                "ID": event_product.ID,
                "Product_Type": "event",
                "Package_Type": event_product.Package_Type,
                "Sell_Price": event_product.Sell_Price,
                "Original_Price": event_product.Original_Price,
                "Product_Name": event_info.Event_Name if event_info else f"Event {event_product.ID}",
                "Product_Description": event_info.Event_Description if event_info else f"Description {event_product.ID}",
                "Precautions": event_info.Precautions if event_info else f"Precautions {event_product.ID}"
            }
            
            event_products_list.append(event_product_data)

        # Procedure 데이터 조회 및 추가
        if element_ids or bundle_ids or custom_ids or sequence_ids:
            procedure_dict = process_procedure_data(
                db,
                query_results_event_product,
                element_ids,
                bundle_ids,
                custom_ids,
                sequence_ids
            )
            
            # Procedure 정보를 각 상품에 추가 (한 번에 merge)
            for product in event_products_list:
                product.update(
                    procedure_dict.get(product["ID"], {
                        "procedure_names": [],
                        "class_types": []
                    })
                )
        else:
            # Procedure가 없는 경우 빈 배열 추가
            for product in event_products_list:
                product.update({
                    "procedure_names": [],
                    "class_types": []
                })
        
        # 최종 응답 반환
        return event_products_list
    
    finally:
        db.close()


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

