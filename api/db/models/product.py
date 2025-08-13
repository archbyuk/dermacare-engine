from sqlalchemy import Column, Integer, String, Float
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

    def __repr__(self):
        return f"<ProductStandard(ID={self.ID}, Package_Type='{self.Package_Type}')>"
