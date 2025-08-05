from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from ..base import Base

class ProcedureElement(Base):
    """단일 시술 상세 정보 테이블"""
    __tablename__ = "Procedure_Element"

    ID = Column(Integer, primary_key=True, autoincrement=True, comment='단일 시술 ID')
    Release = Column(Boolean, default=True, comment='비/활성 여부')
    Class_Major = Column(String(100), comment='시술 대분류 (enum ClassMajor)')
    Class_Sub = Column(String(100), comment='시술 중분류 (enum ClassSub)')
    Class_Detail = Column(String(100), comment='시술 상세분류 (enum ClassDetail)')
    Class_Type = Column(String(100), comment='시술 속성 (enum ClassType)')
    Name = Column(String(255), nullable=False, comment='단일 시술 이름')
    Description = Column(Text, comment='단일 시술 설명')
    Position_Type = Column(String(100), comment='시술 행위자 (enum ProcedureType)')
    Cost_Time = Column(Integer, comment='소요 시간 (분)')
    Plan_State = Column(Boolean, default=False, comment='플랜 여부')
    Plan_Count = Column(Integer, default=1, comment='플랜 횟수')
    Consum_1_ID = Column(Integer, ForeignKey('Consumables.ID', ondelete='SET NULL'), comment='소모품 1 ID')
    Consum_1_Count = Column(Integer, default=1, comment='소모품 1 개수')
    Procedure_Cost = Column(Integer, comment='시술 원가')
    Base_Price = Column(Integer, comment='기준 가격')

    # 관계 설정
    consumable_1 = relationship("Consumables", back_populates="procedure_elements")
    procedure_bundles = relationship("ProcedureBundle", back_populates="element")
    procedure_sequences = relationship("ProcedureSequence", back_populates="element")

    __table_args__ = (
        Index('idx_class_major', 'Class_Major'),
        Index('idx_class_sub', 'Class_Sub'),
        Index('idx_position_type', 'Position_Type'),
        Index('idx_release', 'Release'),
        {'mysql_engine': 'InnoDB'},
    )

    def __repr__(self):
        return f"<ProcedureElement(ID={self.ID}, Name='{self.Name}', Class_Major='{self.Class_Major}')>"