"""
    DermaCare API 메인 애플리케이션

    FastAPI 애플리케이션의 진입점입니다.
    모든 라우터를 등록하고 기본 설정을 관리합니다.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.health import health_router
from api.excel import excel_router
from read import read_router
from api.auth import router as auth_router
from api.admin_tables import global_router, consumables_router, elements_router, bundles_router, customs_router, sequences_router, products_router, membership_router

app = FastAPI(
    title="DermaCare API",
    description="DermaCare 시술 관리 시스템 API - Excel 파싱 및 데이터 관리",
    version="2.0.0"
)

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (개발용)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# 라우터 등록
app.include_router(health_router)
app.include_router(excel_router)
app.include_router(read_router)
app.include_router(auth_router)
app.include_router(global_router)
app.include_router(consumables_router)
app.include_router(elements_router)
app.include_router(bundles_router)
app.include_router(customs_router)
app.include_router(sequences_router)
app.include_router(products_router)
app.include_router(membership_router)

@app.get("/")
def root():
    """API 루트 엔드포인트"""
    return {
        "message": "DermaCare API Server",
        "version": "2.0.0",
        "description": "Excel 파일 업로드 및 파싱을 지원하는 시술 조회 시스템",
        "endpoints": {
            "health": "/health",
            "excel": "/excel",
            "read": "/read",
            "auth": "/auth",
            "global": "/global",
            "consumables": "/consumables",
            "elements": "/elements",
            "bundles": "/bundles",
            "customs": "/customs",
            "sequences": "/sequences",
            "products": "/products",
            "membership": "/membership",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }