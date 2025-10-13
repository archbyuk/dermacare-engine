"""
DermaCare Database Package
데이터베이스 연결, 세션 관리, 모델 정의를 담당하는 패키지

테이블 구조 (14개 테이블):
- 기본 테이블: Consumables, Global, Enum
- 정보 테이블: InfoEvent, InfoMembership, InfoStandard
- 시술 관련: ProcedureElement, ProcedureClass, ProcedureBundle, ProcedureCustom, ProcedureSequence
- 멤버십: Membership
- 상품 테이블: ProductEvent, ProductStandard
"""

# 기본 데이터베이스 구성요소
from .base import Base, metadata
from .session import engine, SessionLocal, get_db, async_engine, AsyncSessionLocal, get_async_db

# ORM models
from .models.enum import Enum   # 자료형
from .models.consumables import Consumables   # 소모품
from .models.global_config import Global   # 짬통
from .models.info import InfoEvent, InfoMembership, InfoStandard   # 정보 모델들
from .models.procedure import (
    ProcedureElement, 
    ProcedureClass, 
    ProcedureBundle, 
    ProcedureCustom, 
    ProcedureSequence
)   # 시술 관련 모델들
from .models.membership import Membership   # 멤버십 모델들
from .models.product import ProductEvent, ProductStandard   # 상품 모델들

__all__ = [
    # 데이터베이스 기본 구성요소
    "Base", 
    "metadata", 
    "engine", 
    "SessionLocal", 
    "get_db",
    "async_get_db",
    "async_engine",
    "AsyncSessionLocal",
    "get_async_db",
    
    # 기본 모델들
    "Enum",
    "Consumables", 
    "Global",
    
    # 정보 모델들
    "InfoEvent",
    "InfoMembership",
    "InfoStandard",
    
    # 시술 관련 모델들
    "ProcedureElement",
    "ProcedureClass",
    "ProcedureBundle", 
    "ProcedureCustom",
    "ProcedureSequence",
    
    # 멤버십 모델들
    "Membership",
    
    # 상품 모델들
    "ProductEvent",
    "ProductStandard",
    
    # 유틸리티 함수들
    "create_tables",
    "drop_tables",
    "recreate_tables",
    "get_table_list",
]

def create_tables():
    """
    모든 테이블을 생성합니다.
    기존 테이블이 있어도 에러가 발생하지 않습니다.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 모든 테이블이 성공적으로 생성되었습니다.")
        return True
    except Exception as e:
        print(f"❌ 테이블 생성 중 오류 발생: {e}")
        return False

def drop_tables():
    """
    모든 테이블을 삭제합니다.
    주의: 모든 데이터가 삭제됩니다!
    """
    try:
        Base.metadata.drop_all(bind=engine)
        print("✅ 모든 테이블이 성공적으로 삭제되었습니다.")
        return True
    except Exception as e:
        print(f"❌ 테이블 삭제 중 오류 발생: {e}")
        return False

def recreate_tables():
    """
    모든 테이블을 삭제하고 다시 생성합니다.
    주의: 모든 데이터가 삭제됩니다!
    """
    print("🔄 테이블 재생성을 시작합니다...")
    
    # 기존 테이블 삭제
    if drop_tables():
        # 새 테이블 생성
        if create_tables():
            print("🎯 테이블 재생성이 완료되었습니다!")
            return True
    
    print("❌ 테이블 재생성에 실패했습니다.")
    return False

def get_table_list():
    """
    현재 정의된 모든 테이블 목록을 반환합니다.
    """
    tables = []
    for table_name, table in Base.metadata.tables.items():
        tables.append({
            'name': table_name,
            'columns': len(table.columns),
            'foreign_keys': len(table.foreign_keys),
            'indexes': len(table.indexes)
        })
    return tables

# 개발용 편의 함수
def print_table_info():
    """
    테이블 정보를 보기 좋게 출력합니다.
    """
    tables = get_table_list()
    print("\n📋 DermaCare 데이터베이스 테이블 목록:")
    print("-" * 60)
    print(f"{'테이블명':<20} {'컬럼수':<8} {'외래키':<8} {'인덱스':<8}")
    print("-" * 60)
    
    for table in tables:
        print(f"{table['name']:<20} {table['columns']:<8} {table['foreign_keys']:<8} {table['indexes']:<8}")
    
    print("-" * 60)
    print(f"총 {len(tables)}개 테이블")

# 스크립트로 직접 실행될 때
if __name__ == "__main__":
    print("DermaCare Database Management")
    print_table_info()