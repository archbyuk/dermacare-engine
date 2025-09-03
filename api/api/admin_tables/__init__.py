"""
    관리자용 테이블 API 패키지

    이 패키지는 관리자가 사용하는 테이블 CRUD API들을 관리합니다.
"""

from .global_config import global_router
from .consumables import consumables_router
from .elements import elements_router
from .bundles import bundles_router
from .customs import customs_router
from .sequences import sequences_router
from .products import products_router
from .membership import membership_router

__all__ = [
    "global_router",
    "consumables_router",
    "elements_router",
    "bundles_router",
    "customs_router",
    "sequences_router",
    "products_router",
    "membership_router"
]
