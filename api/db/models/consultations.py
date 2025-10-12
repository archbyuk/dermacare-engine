from sqlalchemy import Column, BigInteger, String, Float, Text, Date, DateTime, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from ..base import Base

class Consultations(Base):
    """상담 정보 테이블"""
    __tablename__ = "Consultations"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='PK: 상담 고유 ID')
    consultation_date = Column(Date, comment='상담 일자')
    start_time = Column(DateTime, comment='상담 시작시간 (KST 기준)')
    end_time = Column(DateTime, comment='상담 종료시간 (KST 기준)')
    customer_name = Column(String(50), comment='고객명 (외국인 고려)')
    chart_number = Column(BigInteger, comment='차트번호')
    inflow_path = Column(String(50), comment='유입경로 (여러 항목일 경우 , 구분)')
    consultation_type = Column(String(100), comment='상담유형 (여러 항목일 경우 , 구분)')
    goal_treatment = Column(Boolean, comment='목표시술 여부')
    concern_type = Column(String(255), comment='고민유형 (여러 항목일 경우 , 구분)')
    purchased_items = Column(String(255), comment='구매상품 (여러 항목일 경우 , 구분)')
    is_upselling = Column(Boolean, comment='업셀링 여부')
    has_membership = Column(String(50), comment='보유 맴버십')
    payment_type = Column(String(50), comment='결제타입')
    consultation_content = Column(Text, comment='상담내용')
    discount_rate = Column(Float, comment='추가할인율 (0~10%, 음수 없음)')
    total_payment = Column(BigInteger, comment='결제액 (원 단위, 음수 없음)')
    created_at = Column(TIMESTAMP, default=func.current_timestamp(), comment='기록 생성 시점')
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='수정 시점')