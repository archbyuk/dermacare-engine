from sqlalchemy import Column, Integer, String, Text, Float, Index
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
    Plan_Interval = Column(Integer, comment='시술 재방문 주기 (일)')
    Consum_1_ID = Column(Integer, comment='소모품 1 ID')
    Consum_1_Count = Column(Integer, comment='소모품 1 개수')
    Procedure_Level = Column(String(50), comment='시술 난이도 (매우쉬움, 쉬움, 보통, 어려움, 매우어려움)')
    Procedure_Cost = Column(Integer, comment='시술 원가')
    Price = Column(Integer, comment='시술 가격')

    # 인덱스 추가
    __table_args__ = (
        Index('idx_element_release', 'Release'),
        Index('idx_element_class_major', 'Class_Major'),
        Index('idx_element_class_sub', 'Class_Sub'),
        Index('idx_element_class_detail', 'Class_Detail'),
        Index('idx_element_name', 'Name'),
        Index('idx_element_consum', 'Consum_1_ID'),
        Index('idx_element_price', 'Price'),
    )

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

    # 인덱스 추가
    __table_args__ = (
        Index('idx_class_release', 'Release'),
        Index('idx_class_major', 'Class_Major'),
        Index('idx_class_sub', 'Class_Sub'),
        Index('idx_class_detail', 'Class_Detail'),
        Index('idx_class_type', 'Class_Type'),
    )

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
    Price_Ratio = Column(Float, nullable=True, comment='가격 비율')

    # 인덱스 추가 - 연쇄 업데이트를 위한 핵심 인덱스
    __table_args__ = (
        Index('idx_bundle_release', 'Release'),
        Index('idx_bundle_element_id', 'Element_ID'),  # 핵심 인덱스
        Index('idx_bundle_name', 'Name'),
        Index('idx_bundle_element_cost', 'Element_Cost'),
    )

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
    Custom_Count = Column(Integer, nullable=True, comment='시술 횟수')
    Element_Limit = Column(Integer, nullable=True, comment='개별 횟수 제한')
    Element_Cost = Column(Integer, comment='시술 원가')
    Price_Ratio = Column(Float, nullable=True, comment='가격 비율')

    # 인덱스 추가 - 연쇄 업데이트를 위한 핵심 인덱스
    __table_args__ = (
        Index('idx_custom_release', 'Release'),
        Index('idx_custom_element_id', 'Element_ID'),  # 핵심 인덱스
        Index('idx_custom_name', 'Name'),
        Index('idx_custom_element_cost', 'Element_Cost'),
    )

    def __repr__(self):
        return f"<ProcedureCustom(GroupID={self.GroupID}, ID={self.ID}, Name='{self.Name}')>"


class ProcedureSequence(Base):
    """시술 순서 테이블"""
    __tablename__ = "Procedure_Sequence"

    GroupID = Column(Integer, primary_key=True, comment='그룹 ID')
    ID = Column(Integer, primary_key=True, comment='시퀀스 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Name = Column(String(255), nullable=True, comment='시퀀스 이름')
    Step_Num = Column(Integer, comment='순서 번호')
    Element_ID = Column(Integer, nullable=True, comment='단일 시술 ID')
    Bundle_ID = Column(Integer, nullable=True, comment='번들 시술 ID')
    Custom_ID = Column(Integer, nullable=True, comment='커스텀 시술 ID')
    Sequence_Interval = Column(Integer, nullable=True, comment='재방문 주기 (일)')
    Procedure_Cost = Column(Integer, comment='시술 원가')
    Price_Ratio = Column(Float, nullable=True, comment='가격 비율')

    # 인덱스 추가 - 연쇄 업데이트를 위한 핵심 인덱스
    __table_args__ = (
        Index('idx_sequence_release', 'Release'),
        Index('idx_sequence_element_id', 'Element_ID'),  # 핵심 인덱스
        Index('idx_sequence_bundle_id', 'Bundle_ID'),    # 핵심 인덱스
        Index('idx_sequence_custom_id', 'Custom_ID'),    # 핵심 인덱스
        Index('idx_sequence_step_num', 'Step_Num'),
        Index('idx_sequence_procedure_cost', 'Procedure_Cost'),
    )

    def __repr__(self):
        return f"<ProcedureSequence(GroupID={self.GroupID}, ID={self.ID}, Step_Num={self.Step_Num})>"
