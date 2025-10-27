"""
    DermaCare API 메인 애플리케이션

    FastAPI 애플리케이션의 진입점입니다.
    모든 라우터를 등록하고 기본 설정을 관리합니다.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from security.verification_user import verification_jwt
from fastapi.responses import JSONResponse
from api.health import health_router
from upload import upload_router
from list.router import list_router
from consultations.router import consultations_router
from consultations.endpoints.member import member_router
from auth import auth_router
from new_auth.new_login import router as new_auth_router
from new_auth.new_token_reissue import router as new_token_reissue_router
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
        "http://localhost:3333",
        "https://localhost:3334",
        "https://dermacare-view.vercel.app",
        "https://dev.facefilter.co.kr",
    ],
    allow_credentials=True, # 쿠키 전달 허용
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Gzip 압축 설정 (600KB 이상 응답만 압축)
app.add_middleware(GZipMiddleware, minimum_size=614400)

# JWT 인증 미들웨어 (모든 요청에 적용)
@app.middleware("http")
async def jwt_auth_middleware(request: Request, pass_middleware):
    # 인증이 불필요한 경로들
    auth_exempt_paths = [
        "/health",
        "/docs", 
        "/redoc",
        "/openapi.json",
        "/auth/login",
        "/new_login/new_login",
        "/new_token_reissue/refresh"
    ]
    
    # 인증 불필요한 경로는 통과
    if request.url.path in auth_exempt_paths:
        return await pass_middleware(request)
    
    # JWT 토큰 검증
    try:
        print(f"🔍 DEBUG: request.url.path = {request.ora}")
        user_info = verification_jwt(request)
        # request.state: 각 HTTP 요청마다 독립적으로 존재하는 임시 저장소로, 사용자 인증상태 검증 후 user정보를 저장하여 사용
        request.state.user = user_info
        
    
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    
    return await pass_middleware(request)

# 라우터 등록
app.include_router(health_router)
app.include_router(upload_router)
app.include_router(list_router)
app.include_router(auth_router)
app.include_router(new_auth_router, prefix="/new_login", tags=["New Auth"])
app.include_router(new_token_reissue_router, prefix="/new_token_reissue", tags=["New Token Reissue"])
app.include_router(global_router)
app.include_router(consumables_router)
app.include_router(elements_router)
app.include_router(bundles_router)
app.include_router(customs_router)
app.include_router(sequences_router)
app.include_router(products_router)
app.include_router(membership_router)
app.include_router(consultations_router)
app.include_router(member_router, prefix="/consultations", tags=["Consultation Members"])

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
            "new-auth": "/new_login",
            "global": "/global",
            "consumables": "/consumables",
            "elements": "/elements",
            "bundles": "/bundles",
            "customs": "/customs",
            "sequences": "/sequences",
            "products": "/products",
            "membership": "/membership",
            "consultations": "/consultations",
            "consultation-members": "/consultations/consultation-member",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }