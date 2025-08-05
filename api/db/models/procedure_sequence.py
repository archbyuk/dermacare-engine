from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from ..base import Base

class ProcedureSequence(Base):
    """번들 및 단일 시술 순서대로 나열한 시퀀스 정보"""
    __tablename__ = "Procedure_Sequence"

    GroupID = Column(Integer, nullable=False, comment='시퀀스 그룹 ID')
    ID = Column(Integer, primary_key=True, autoincrement=True, comment='고유 ID')
    Release = Column(Boolean, default=True, comment='비/활성 여부')
    Step_Num = Column(Integer, nullable=False, comment='시술 순서')
    Element_ID = Column(Integer, ForeignKey('Procedure_Element.ID', ondelete='CASCADE'), comment='단일 시술 ID')
    Bundle_ID = Column(Integer, ForeignKey('Procedure_Bundle.ID', ondelete='CASCADE'), comment='번들 ID')
    Procedure_Cost = Column(Integer, comment='시술 원가')
    Price_Ratio = Column(Float, comment='가격 비율')

    # 관계 설정
    element = relationship("ProcedureElement", back_populates="procedure_sequences")
    bundle = relationship("ProcedureBundle", back_populates="procedure_sequences")

    __table_args__ = (
        Index('idx_group_id', 'GroupID'),
        Index('idx_step_num', 'Step_Num'),
        Index('idx_element_id', 'Element_ID'),
        Index('idx_bundle_id', 'Bundle_ID'),
        Index('idx_release', 'Release'),
        {'mysql_engine': 'InnoDB'},
    )

    def __repr__(self):
        return f"<ProcedureSequence(ID={self.ID}, GroupID={self.GroupID}, Step_Num={self.Step_Num})>"