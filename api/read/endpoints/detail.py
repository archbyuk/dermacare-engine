"""
    [ '상품 상세 조회' 엔드포인트 ]
    클릭된 상품의 상세 정보를 조회합니다.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from ..schema import ProductDetailResponse
from ..services.common_service import get_product_by_type, build_product_basic_info
from ..services.detail_service import add_package_details

# FastAPI 라우터 생성
router = APIRouter()

"""
    상품 상세 조회:
    
        클릭된 상품의 상세 정보를 조회합니다.
        해당 '상품'에 속한 모든 Element, Bundle, Sequence 정보를 전부 조회합니다.
"""
# response_model=ProductDetailResponse
@router.get("/products/{product_id}")
def get_product_detail(
    product_id: int,
    product_type: str = Query(..., description="상품 타입 (standard/event)"),
    db: Session = Depends(get_db)
):
    try:
        # product_id, product_type에 따른 상품 조회
        product = get_product_by_type(product_id, product_type, db)
        
        # 상품 기본 정보 구성: build_product_basic_info 함수를 호출하여 product_data를 생성
        product_data = build_product_basic_info(product, product_type, db)

        """
            build_product_basic_info 함수를 호출하여 생성된 product_data:
            
                product_data:
                    {
                        "ID": product.ID,
                        "Product_Type": product_type,
                        "Package_Type": product.Package_Type,
                        "Element_ID": product.Element_ID,
                        "Bundle_ID": product.Bundle_ID,
                        "Custom_ID": product.Custom_ID,
                        "Sequence_ID": product.Sequence_ID,
                        "Sell_Price": product.Sell_Price,
                        "Original_Price": product.Original_Price,
                        "Discount_Rate": product.Discount_Rate,
                        "Validity_Period": product.Validity_Period,
                        "VAT": product.VAT,
                        "Covered_Type": product.Covered_Type,
                        "Taxable_Type": product.Taxable_Type,
                        (
                            "Standard_Start_Date": product.Standard_Start_Date,
                            "Standard_End_Date": product.Standard_End_Date,
                                :OR:
                            "Event_Start_Date": product.Event_Start_Date,
                            "Event_End_Date": product.Event_End_Date
                        )
                    }
        """
        
        # Package_Type별 상세 정보 추가: add_package_details 함수를 호출하여 product_data에 추가 후 반환
        add_package_details(product, product_data, db)
        
        # 상품 상세 정보 조회 완료 - 기존 응답 구조 유지
        return {
            "status": "success",
            "message": "상품 상세 조회 완료",
            "data": product_data
        }
        
    
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상품 상세 조회 중 오류 발생: {str(e)}"
        )