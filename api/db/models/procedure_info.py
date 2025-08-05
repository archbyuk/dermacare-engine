from sqlalchemy import Column, Integer, String, Boolean, Text, Index
from sqlalchemy.orm import relationship
from ..base import Base

class ProcedureInfo(Base):
    """시술 상세 정보 테이블"""
    __tablename__ = "Procedure_Info"

    ID = Column(Integer, primary_key=True, autoincrement=True, comment='고유 ID')
    Release = Column(Boolean, default=True, comment='비/활성 여부')
    Procedure_ID = Column(Integer, nullable=False, comment='어떤 시술(Procedure)을 설명하는지 가리키는 논리적 참조 (ID)')
    Procedure_Name = Column(String(255), nullable=False, comment='시술 이름')
    Procedure_Description = Column(Text, comment='시술 설명')
    Precautions = Column(Text, comment='주의사항')

    # 관계 설정
    procedure_products = relationship("ProcedureProduct", back_populates="procedure_info")

    __table_args__ = (
        Index('idx_procedure_id', 'Procedure_ID'),
        Index('idx_release', 'Release'),
        {'mysql_engine': 'InnoDB'},
    )

    def __repr__(self):
        return f"<ProcedureInfo(ID={self.ID}, Procedure_Name='{self.Procedure_Name}')>"