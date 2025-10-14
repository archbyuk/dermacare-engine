"""
    Upload 도메인 메인 라우터
    xcel 파일 업로드 관련 모든 엔드포인트를 통합 관리
"""

from fastapi import APIRouter
from .endpoints.file_upload import router as file_upload_router

# 메인 라우터 생성
upload_router = APIRouter(tags=["Upload"])

# 하위 라우터들 포함
upload_router.include_router(file_upload_router)
