"""
DermaCare ORM Models

이 모듈은 DermaCare 시술 관리 시스템의 모든 데이터베이스 모델을 포함합니다.
"""

from .database import Base, engine, SessionLocal, get_db
from .enum import Enum
from .consumables import Consumables
from .global_config import Global
from .procedure_element import ProcedureElement
from .procedure_bundle import ProcedureBundle
from .procedure_sequence import ProcedureSequence
from .procedure_info import ProcedureInfo
from .procedure_product import ProcedureProduct

# 모든 모델을 리스트로 내보내기
__all__ = [
    "Base",
    "engine", 
    "SessionLocal",
    "get_db",
    "Enum",
    "Consumables", 
    "Global",
    "ProcedureElement",
    "ProcedureBundle",
    "ProcedureSequence", 
    "ProcedureInfo",
    "ProcedureProduct",
]

# 테이블 생성 함수
def create_tables():
    """모든 테이블을 데이터베이스에 생성합니다."""
    Base.metadata.create_all(bind=engine)

# 테이블 삭제 함수
def drop_tables():
    """모든 테이블을 데이터베이스에서 삭제합니다."""
    Base.metadata.drop_all(bind=engine)
