from sqlalchemy import Column, Integer, String, Text, Float, Boolean
from ..base import Base

class ProcedureElement(Base):
    """시술 요소 테이블"""
    __tablename__ = "Procedure_Element"

    ID = Column(Integer, primary_key=True, comment='시술 요소 고유 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Class_Major = Column(String(50), comment='시술 대분류')
    Class_Sub = Column(String(50), comment='시술 중분류')
    Class_Detail = Column(String(50), comment='시술 상세분류')
    Class_Type = Column(String(50), comment='시술 속성')
    Name = Column(String(255), comment='단일 시술 이름')
    description = Column(Text, comment='단일 시술 설명')
    Position_Type = Column(String(50), comment='시술자 타입')
    Cost_Time = Column(Float, comment='소요 시간 (분)')
    Plan_State = Column(Integer, comment='플랜 여부 (0: False, 1: True, NULL: Unknown)')
    Plan_Count = Column(Integer, comment='플랜 횟수')
    Consum_1_ID = Column(Integer, comment='소모품 1 ID')
    Consum_1_Count = Column(Integer, comment='소모품 1 개수')
    Procedure_Level = Column(String(50), comment='시술 난이도 (매우쉬움, 쉬움, 보통, 어려움, 매우어려움)')
    Procedure_Cost = Column(Integer, comment='시술 원가')
    Price = Column(Integer, comment='시술 가격')

    def __repr__(self):
        return f"<ProcedureElement(ID={self.ID}, Name='{self.Name}')>"


class ProcedureClass(Base):
    """시술 분류 테이블"""
    __tablename__ = "Procedure_Class"

    GroupID = Column(Integer, primary_key=True, comment='그룹 ID')
    ID = Column(Integer, primary_key=True, comment='분류 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Class_Major = Column(String(50), comment='시술 대분류 (레이저, 초음파 등)')
    Class_Sub = Column(String(50), comment='시술 중분류 (리팟, 젠틀맥스 등)')
    Class_Detail = Column(String(50), comment='시술 상세분류 (안면 제모, 바디 제모 등)')
    Class_Type = Column(String(50), comment='시술 속성 (제모, 쁘띠 등)')

    def __repr__(self):
        return f"<ProcedureClass(GroupID={self.GroupID}, ID={self.ID}, Class_Major='{self.Class_Major}')>"


class ProcedureBundle(Base):
    """시술 번들 테이블"""
    __tablename__ = "Procedure_Bundle"

    GroupID = Column(Integer, primary_key=True, comment='그룹 ID')
    ID = Column(Integer, primary_key=True, comment='번들 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Name = Column(String(255), nullable=True, comment='번들 이름')
    Description = Column(Text, nullable=True, comment='번들 설명')
    Element_ID = Column(Integer, comment='단일 시술 ID')
    Element_Cost = Column(Integer, comment='시술 원가')
    Price_Ratio = Column(Float, comment='가격 비율')

    def __repr__(self):
        return f"<ProcedureBundle(GroupID={self.GroupID}, ID={self.ID}, Name='{self.Name}')>"


class ProcedureCustom(Base):
    """커스텀 시술 테이블"""
    __tablename__ = "Procedure_Custom"

    GroupID = Column(Integer, primary_key=True, comment='그룹 ID')
    ID = Column(Integer, primary_key=True, comment='커스텀 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Name = Column(String(255), comment='커스텀 시술 이름')
    Description = Column(Text, comment='커스텀 시술 설명')
    Element_ID = Column(Integer, comment='단일 시술 ID')
    Custom_Count = Column(Integer, comment='시술 횟수')
    Element_Limit = Column(Integer, comment='개별 횟수 제한')
    Element_Cost = Column(Integer, comment='시술 원가')
    Price_Ratio = Column(Float, comment='가격 비율')

    def __repr__(self):
        return f"<ProcedureCustom(GroupID={self.GroupID}, ID={self.ID}, Name='{self.Name}')>"


class ProcedureSequence(Base):
    """시술 순서 테이블"""
    __tablename__ = "Procedure_Sequence"

    GroupID = Column(Integer, primary_key=True, comment='그룹 ID')
    ID = Column(Integer, primary_key=True, comment='시퀀스 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Step_Num = Column(Integer, comment='순서 번호')
    Element_ID = Column(Integer, comment='단일 시술 ID')
    Bundle_ID = Column(Integer, comment='번들 시술 ID')
    Custom_ID = Column(Integer, comment='커스텀 시술 ID')
    Procedure_Cost = Column(Integer, comment='시술 원가')
    Price_Ratio = Column(Float, comment='가격 비율')

    def __repr__(self):
        return f"<ProcedureSequence(GroupID={self.GroupID}, ID={self.ID}, Step_Num={self.Step_Num})>"
