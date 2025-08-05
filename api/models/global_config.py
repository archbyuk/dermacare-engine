from sqlalchemy import Column, Integer
from .database import Base


class Global(Base):
    """ 짬통 테이블: 글로벌 설정 """
    __tablename__ = "Global"

    ID = Column(Integer, primary_key=True, autoincrement=True, comment='고유 ID')
    Doc_Price_Minute = Column(Integer, comment='의사 인건비 (분당)')

    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )

    def __repr__(self):
        return f"<Global(ID={self.ID}, Doc_Price_Minute={self.Doc_Price_Minute})>"