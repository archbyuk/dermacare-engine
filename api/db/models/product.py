from sqlalchemy import Column, Integer, String, Float, Index
from ..base import Base

class ProductEvent(Base):
    """이벤트 상품 테이블"""
    __tablename__ = "Product_Event"

    ID = Column(Integer, primary_key=True, comment='이벤트 상품 고유 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Package_Type = Column(String(50), comment='패키지 타입')
    Element_ID = Column(Integer, comment='단일 시술 ID')
    Bundle_ID = Column(Integer, comment='번들 시술 ID')
    Custom_ID = Column(Integer, comment='커스텀 시술 ID')
    Sequence_ID = Column(Integer, comment='시퀀스 시술 ID')
    Event_Info_ID = Column(Integer, comment='이벤트 정보 ID')
    Procedure_Cost = Column(Integer, comment='시술 원가')
    Sell_Price = Column(Integer, comment='실제 판매가')
    Discount_Rate = Column(Float, comment='할인율')
    Original_Price = Column(Integer, comment='정상가')
    Margin = Column(Integer, comment='마진값')
    Margin_Rate = Column(Float, comment='마진율')
    Event_Start_Date = Column(String(20), comment='이벤트 시작일')
    Event_End_Date = Column(String(20), comment='이벤트 종료일')
    Validity_Period = Column(Integer, comment='유효기간 (일)')
    VAT = Column(Integer, comment='부가세')
    Covered_Type = Column(String(20), comment='급여분류 (급여/비급여)')
    Taxable_Type = Column(String(20), comment='과세분류 (과세/면세)')
    Procedure_Grade = Column(String(50), comment='시술 등급')

    # 인덱스 추가 - 연쇄 업데이트를 위한 핵심 인덱스
    __table_args__ = (
        Index('idx_event_release', 'Release'),
        Index('idx_event_element_id', 'Element_ID'),    # 핵심 인덱스
        Index('idx_event_bundle_id', 'Bundle_ID'),      # 핵심 인덱스
        Index('idx_event_custom_id', 'Custom_ID'),      # 핵심 인덱스
        Index('idx_event_sequence_id', 'Sequence_ID'),  # 핵심 인덱스
        Index('idx_event_package_type', 'Package_Type'),
        Index('idx_event_sell_price', 'Sell_Price'),
        Index('idx_event_start_date', 'Event_Start_Date'),
        Index('idx_event_end_date', 'Event_End_Date'),
        Index('idx_event_procedure_grade', 'Procedure_Grade'),
    )

    def __repr__(self):
        return f"<ProductEvent(ID={self.ID}, Package_Type='{self.Package_Type}', Event_Start_Date={self.Event_Start_Date})>"


class ProductStandard(Base):
    """표준 상품 테이블"""
    __tablename__ = "Product_Standard"

    ID = Column(Integer, primary_key=True, comment='표준 상품 고유 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Package_Type = Column(String(50), comment='패키지 타입')
    Element_ID = Column(Integer, comment='단일 시술 ID')
    Bundle_ID = Column(Integer, comment='번들 시술 ID')
    Custom_ID = Column(Integer, comment='커스텀 시술 ID')
    Sequence_ID = Column(Integer, comment='시퀀스 시술 ID')
    Standard_Info_ID = Column(Integer, comment='표준 정보 ID')
    Procedure_Cost = Column(Integer, comment='시술 원가')
    Sell_Price = Column(Integer, comment='실제 판매가')
    Discount_Rate = Column(Float, comment='할인율')
    Original_Price = Column(Integer, comment='정상가')
    Margin = Column(Integer, comment='마진값')
    Margin_Rate = Column(Float, comment='마진율')
    Standard_Start_Date = Column(String(20), comment='상품 노출 시작일')
    Standard_End_Date = Column(String(20), comment='상품 노출 종료일')
    Validity_Period = Column(Integer, comment='유효기간 (일)')
    VAT = Column(Integer, comment='부가세')
    Covered_Type = Column(String(20), comment='급여분류 (급여/비급여)')
    Taxable_Type = Column(String(20), comment='과세분류 (과세/면세)')
    Procedure_Grade = Column(String(50), comment='시술 등급')

    # 인덱스 추가 - 연쇄 업데이트를 위한 핵심 인덱스
    __table_args__ = (
        Index('idx_standard_release', 'Release'),
        Index('idx_standard_element_id', 'Element_ID'),    # 핵심 인덱스
        Index('idx_standard_bundle_id', 'Bundle_ID'),      # 핵심 인덱스
        Index('idx_standard_custom_id', 'Custom_ID'),      # 핵심 인덱스
        Index('idx_standard_sequence_id', 'Sequence_ID'),  # 핵심 인덱스
        Index('idx_standard_package_type', 'Package_Type'),
        Index('idx_standard_sell_price', 'Sell_Price'),
        Index('idx_standard_start_date', 'Standard_Start_Date'),
        Index('idx_standard_end_date', 'Standard_End_Date'),
        Index('idx_standard_procedure_grade', 'Procedure_Grade'),
    )

    def __repr__(self):
        return f"<ProductStandard(ID={self.ID}, Package_Type='{self.Package_Type}')>"
