from sqlalchemy import Column, Integer, String
from ..base import Base

class Enum(Base):
    """열거형 테이블"""
    __tablename__ = "Enum"

    enum_type = Column(String(50), primary_key=True, comment='열거형 타입명')
    id = Column(Integer, primary_key=True, comment='열거형 ID')
    name = Column(String(255), comment='열거형 이름')

    def __repr__(self):
        return f"<Enum(enum_type='{self.enum_type}', id={self.id}, name='{self.name}')>"
