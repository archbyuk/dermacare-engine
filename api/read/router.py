"""
Read 도메인 메인 라우터
데이터 조회 관련 모든 엔드포인트를 통합 관리
"""

from fastapi import APIRouter
from .endpoints.list import router as list_router
from .endpoints.detail import router as detail_router

# 메인 라우터 생성
read_router = APIRouter(prefix="/read", tags=["Read"])

# 하위 라우터들을 포함 (순서 중요: 구체적인 경로가 먼저)
read_router.include_router(list_router)     # 상품 전체 목록 조회 라우터
read_router.include_router(detail_router)   # 특정 상품 상세 조회 라우터

# 루트 엔드포인트 추가: /read/list, /read/detail
@read_router.get("/")
async def read_info():
    """ Read API 정보 """
    
    return {
        "message": "Read API",
        "description": "데이터 조회 기능을 제공합니다",
        "version": "1.0.0",
        "endpoints": {
            "products": "/read/products",
            "product_detail": "/read/products/{product_id}"
        }
    }
