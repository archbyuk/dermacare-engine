from sqlalchemy import Column, Integer, String, Float
from ..base import Base

class Membership(Base):
    """멤버십 상품 테이블"""
    __tablename__ = "Membership"

    ID = Column(Integer, primary_key=True, comment='멤버십 상품 고유 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Membership_Info_ID = Column(Integer, comment='멤버십 정보 ID')
    Payment_Amount = Column(Integer, comment='결제 금액')
    Bonus_Point = Column(Integer, comment='보너스 포인트')
    Credit = Column(Integer, comment='최종 적립금')
    Discount_Rate = Column(Float, comment='적용 할인율')
    Package_Type = Column(String(50), comment='패키지 타입 (단일시술, 번들, 커스텀 등)')
    Element_ID = Column(Integer, comment='단일 시술 ID')
    Bundle_ID = Column(Integer, comment='번들 시술 ID')
    Custom_ID = Column(Integer, comment='커스텀 시술 ID')
    Sequence_ID = Column(Integer, comment='시퀀스 시술 ID')
    Validity_Period = Column(Integer, comment='유효기간 (일)')
    Release_Start_Date = Column(String(20), comment='판매 시작일')
    Release_End_Date = Column(String(20), comment='판매 종료일')

    def __repr__(self):
        return f"<Membership(ID={self.ID}, Payment_Amount={self.Payment_Amount})>"
