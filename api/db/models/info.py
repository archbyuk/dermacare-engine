from sqlalchemy import Column, Integer, String, Text, Index
from ..base import Base

class InfoEvent(Base):
    """이벤트 정보 테이블"""
    __tablename__ = "Info_Event"

    ID = Column(Integer, primary_key=True, comment='이벤트 정보 고유 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Event_ID = Column(Integer, comment='이벤트 ID')
    Event_Name = Column(String(255), comment='이벤트 이름')
    Event_Description = Column(Text, comment='이벤트 상세 설명')
    Precautions = Column(Text, comment='주의사항')

    # 인덱스 추가
    __table_args__ = (
        Index('idx_info_event_release', 'Release'),
        Index('idx_info_event_id', 'Event_ID'),
        Index('idx_info_event_name', 'Event_Name'),
    )

    def __repr__(self):
        return f"<InfoEvent(ID={self.ID}, Event_Name='{self.Event_Name}')>"


class InfoMembership(Base):
    """멤버십 정보 테이블"""
    __tablename__ = "Info_Membership"

    ID = Column(Integer, primary_key=True, comment='멤버십 정보 고유 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Membership_ID = Column(Integer, comment='멤버십 ID')
    Membership_Name = Column(String(255), comment='멤버십 이름')
    Membership_Description = Column(Text, comment='멤버십 상세 설명')
    Precautions = Column(Text, comment='주의사항')

    # 인덱스 추가
    __table_args__ = (
        Index('idx_info_membership_release', 'Release'),
        Index('idx_info_membership_id', 'Membership_ID'),
        Index('idx_info_membership_name', 'Membership_Name'),
    )

    def __repr__(self):
        return f"<InfoMembership(ID={self.ID}, Membership_Name='{self.Membership_Name}')>"


class InfoStandard(Base):
    """표준 정보 테이블"""
    __tablename__ = "Info_Standard"

    ID = Column(Integer, primary_key=True, comment='표준 정보 고유 ID')
    Release = Column(Integer, comment='활성/비활성 여부')
    Product_Standard_ID = Column(Integer, comment='표준 상품 ID')
    Product_Standard_Name = Column(String(255), comment='표준 상품 이름')
    Product_Standard_Description = Column(Text, comment='표준 상품 상세 설명')
    Precautions = Column(Text, comment='주의사항')

    # 인덱스 추가
    __table_args__ = (
        Index('idx_info_standard_release', 'Release'),
        Index('idx_info_standard_id', 'Product_Standard_ID'),
        Index('idx_info_standard_name', 'Product_Standard_Name'),
    )

    def __repr__(self):
        return f"<InfoStandard(ID={self.ID}, Product_Standard_Name='{self.Product_Standard_Name}')>"
