"""
    상담 관련 라우터
"""

from fastapi import APIRouter
from consultations.endpoints.create import create_router
from consultations.endpoints.read import read_router

# 상담 라우터를 메인 라우터에 포함 (prefix와 tags 설정)
consultations_router = APIRouter(
    prefix="/consultations",
    tags=["Consultations"]
)

# 엔드포인트 라우터 포함
consultations_router.include_router(create_router)
consultations_router.include_router(read_router)
