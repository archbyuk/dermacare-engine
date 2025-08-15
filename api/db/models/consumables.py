from sqlalchemy import Column, Integer, String, Float, Text
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

    def __repr__(self):
        return f"<Consumables(ID={self.ID}, Name='{self.Name}')>"
