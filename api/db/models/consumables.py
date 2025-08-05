from sqlalchemy import Column, Integer, String, Boolean, Text, Float, Index
from sqlalchemy.orm import relationship
from ..base import Base

class Consumables(Base):
    """ 시술에 사용되는 소모품 정보 """
    __tablename__ = "Consumables"

    ID = Column(Integer, primary_key=True, autoincrement=True, comment='소모품 고유 ID')
    Release = Column(Boolean, default=True, comment='비/활성 여부')
    Name = Column(String(255), nullable=False, comment='소모품 이름')
    Description = Column(Text, comment='소모품 설명')
    Unit_Type = Column(String(100), comment='단위 (enum UnitType)')
    I_Value = Column(Integer, comment='정수값')
    F_Value = Column(Float, comment='실수값')
    Price = Column(Integer, comment='소모품 구매 가격')
    Unit_Price = Column(Integer, comment='단위 기준 가격')

    # 관계 설정
    procedure_elements = relationship("ProcedureElement", back_populates="consumable_1")

    __table_args__ = (
        Index('idx_unit_type', 'Unit_Type'),
        Index('idx_release', 'Release'),
        {'mysql_engine': 'InnoDB'},
    )

    def __repr__(self):
        return f"<Consumables(ID={self.ID}, Name='{self.Name}', Unit_Type='{self.Unit_Type}')>"