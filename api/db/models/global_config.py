from sqlalchemy import Column, Integer
from ..base import Base

class Global(Base):
    """전역 설정 테이블"""
    __tablename__ = "Global"

    ID = Column(Integer, primary_key=True, comment='설정 고유 ID')
    Doc_Price_Minute = Column(Integer, comment='의사 인건비 (분당)')
    Aesthetician_Price_Minute = Column(Integer, comment='관리사 인건비 (분당)')

    def __repr__(self):
        return f"<Global(ID={self.ID}, Doc_Price_Minute={self.Doc_Price_Minute})>"
