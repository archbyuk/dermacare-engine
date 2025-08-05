from sqlalchemy import Column, Integer, String, Boolean
from ..base import Base

class Enum(Base):
    """ 짬통 테이블: 공통 코드 테이블 (타입별 Enum 값 저장) """
    __tablename__ = "Enum"

    ID = Column(Integer, primary_key=True, autoincrement=True, comment='고유 ID')
    Release = Column(Boolean, default=True, comment='비/활성 여부')
    Type = Column(String(50), nullable=False, comment='enum 분류 (ex: ProcedureType)')
    Code = Column(String(100), nullable=False, comment='실제 값')
    Name = Column(String(255), comment='표시용 이름')

    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )

    def __repr__(self):
        return f"<Enum(ID={self.ID}, Type='{self.Type}', Code='{self.Code}', Name='{self.Name}')>"