"""
    API 라우터 패키지

    이 패키지는 FastAPI 라우터들을 관리합니다.
"""

from .health import health_router
from .excel import excel_router
from .search import search_router
from .read import read_router
from .sort import sort_router
from .filter import filter_router
from .admin_tables import global_router, consumables_router

__all__ = [
    "health_router", 
    "excel_router", 
    "search_router", 
    "read_router", 
    "sort_router", 
    "filter_router",
    "global_router",
    "consumables_router"
]