"""
    상품 목록 조회 API 메인 라우터
"""

from fastapi import APIRouter
from .endpoints.list import router as products_list_router
from .endpoints.detail import router as products_detail_router

# 메인 라우터 생성
list_router = APIRouter(prefix="/list", tags=["Read"])

# 하위 라우터들을 포함 (순서 중요: 구체적인 경로가 먼저)
list_router.include_router(products_list_router)     # 상품 전체 목록 조회 라우터
list_router.include_router(products_detail_router)   # 특정 상품 상세 조회 라우터