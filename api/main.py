"""
    DermaCare API 메인 애플리케이션

    FastAPI 애플리케이션의 진입점입니다.
    모든 라우터를 등록하고 기본 설정을 관리합니다.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.health import health_router
from upload import upload_router
from read import read_router
from consultations.router import consultations_router
from auth import auth_router
from api.admin_tables import global_router, consumables_router, elements_router, bundles_router, customs_router, sequences_router, products_router, membership_router

app = FastAPI(
    title="FaceFilter API",
    description="페이스필터 데이터 관리 API",
    version="2.0.1"
)

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://loacalhost:3001",
        "https://localhost:3002",
        "https://dermacare-view.vercel.app",
    ],
    allow_credentials=True, # 쿠키 전달 허용
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# 라우터 등록
app.include_router(health_router)
app.include_router(upload_router)
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
app.include_router(consultations_router)

@app.get("/")
def root():
    """API 루트 엔드포인트"""
    return {
        "message": "FaceFilter API Server",
        "version": "2.0.1",
        "description": "페이스필터 데이터 관리 API",
        "endpoints": {
            "health": "/health",
            "upload": "/upload",
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
            "consultations": "/consultations",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }