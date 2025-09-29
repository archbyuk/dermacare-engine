"""
    API 라우터 패키지

    이 패키지는 FastAPI 라우터들을 관리합니다.
"""

from .health import health_router
from .admin_tables import global_router, consumables_router

__all__ = [
    "health_router", 
    "global_router",
    "consumables_router"
]