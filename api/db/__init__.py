"""
    DermaCare Database Package
    데이터베이스 연결, 세션 관리, 모델 정의를 담당하는 패키지
"""

from .base import Base, metadata
from .session import engine, SessionLocal, get_db

from .models.enum import Enum
from .models.consumables import Consumables
from .models.global_config import Global
from .models.procedure_element import ProcedureElement
from .models.procedure_bundle import ProcedureBundle
from .models.procedure_sequence import ProcedureSequence
from .models.procedure_info import ProcedureInfo
from .models.procedure_product import ProcedureProduct

__all__ = [
    "Base", "metadata", "engine", "SessionLocal", "get_db",
    "Enum", "Consumables", "Global", 
    "ProcedureElement", "ProcedureBundle", "ProcedureSequence",
    "ProcedureInfo", "ProcedureProduct"
]

def create_tables():
    Base.metadata.create_all(bind=engine)

def drop_tables():
    Base.metadata.drop_all(bind=engine)