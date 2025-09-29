from sqlalchemy import Column, Integer, String, Float, Text, Index
from ..base import Base

class Consumables(Base):
    """소모품 테이블"""
    __tablename__ = "Consumables"

    ID = Column(Integer, primary_key=True, comment='소모품 고유 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Name = Column(String(255), comment='소모품 이름')
    Description = Column(Text, nullable=True, comment='소모품 상세 설명')
    Unit_Type = Column(String(50), comment='단위 타입 (cc, EA, 개 등)')
    I_Value = Column(Integer, comment='정수값')
    F_Value = Column(Float, comment='실수값')
    Price = Column(Integer, comment='구매가격')
    Unit_Price = Column(Integer, comment='단위별 원가')
    VAT = Column(Integer, comment='부가세')
    Taxable_Type = Column(String(50), comment='과세분류')
    Covered_Type = Column(String(50), comment='급여분류')

    # 인덱스 추가
    __table_args__ = (
        Index('idx_consumables_release', 'Release'),
        Index('idx_consumables_name', 'Name'),
        Index('idx_consumables_unit_type', 'Unit_Type'),
        Index('idx_consumables_price', 'Price'),
        Index('idx_consumables_unit_price', 'Unit_Price'),
    )

    def __repr__(self):
        return f"<Consumables(ID={self.ID}, Name='{self.Name}')>"
