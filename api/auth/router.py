"""
    인증 라우터 통합
"""
from fastapi import APIRouter
from .endpoints.login import router as login_router
from .endpoints.logout import router as logout_router
from .endpoints.token_reissue import router as token_reissue_router

# 메인 라우터
auth_router = APIRouter(tags=["인증"])

# 엔드포인트 등록
auth_router.include_router(login_router)
auth_router.include_router(logout_router)
auth_router.include_router(token_reissue_router)

