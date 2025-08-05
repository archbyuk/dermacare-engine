from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from ..base import Base

class ProcedureBundle(Base):
    """단일 시술을 묶은 번들 시술 정보"""
    __tablename__ = "Procedure_Bundle"

    GroupID = Column(Integer, nullable=False, comment='번들 그룹 ID')
    ID = Column(Integer, primary_key=True, autoincrement=True, comment='고유 ID')
    Release = Column(Boolean, default=True, comment='비/활성 여부')
    Name = Column(String(255), nullable=False, comment='번들 이름')
    Description = Column(Text, comment='번들 설명')
    Element_ID = Column(Integer, ForeignKey('Procedure_Element.ID', ondelete='CASCADE'), nullable=False, comment='단일 시술 ID')
    Element_Cost = Column(Integer, comment='단일 시술 원가')
    Price_Ratio = Column(Float, comment='가격 비율')

    # 관계 설정
    element = relationship("ProcedureElement", back_populates="procedure_bundles")
    procedure_sequences = relationship("ProcedureSequence", back_populates="bundle")

    __table_args__ = (
        Index('idx_group_id', 'GroupID'),
        Index('idx_element_id', 'Element_ID'),
        Index('idx_release', 'Release'),
        {'mysql_engine': 'InnoDB'},
    )

    def __repr__(self):
        return f"<ProcedureBundle(ID={self.ID}, GroupID={self.GroupID}, Name='{self.Name}')>"