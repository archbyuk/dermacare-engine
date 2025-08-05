from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from .database import Base


class ProcedureProduct(Base):
    """최종 시술 상품 테이블 (가격, 유효기간 포함)"""
    __tablename__ = "Procedure_Product"

    ID = Column(Integer, primary_key=True, autoincrement=True, comment='고유 ID')
    Release = Column(Boolean, default=True, comment='비/활성 여부')
    Package_Type = Column(String(100), nullable=False, comment='패키지 타입 (enum PackageType)')
    Procedure_ID = Column(Integer, nullable=False, comment='시술 ID (Package_Type에 따라 참조 대상 변경 - 로직 거쳐야 함)')
    Procedure_Info_ID = Column(Integer, ForeignKey('Procedure_Info.ID', ondelete='SET NULL'), comment='시술 정보 ID (Procedure_Info.ID 참조)')
    Procedure_Cost = Column(Integer, comment='원가')
    Price = Column(Integer, comment='정상가')
    Sell_Price = Column(Integer, comment='판매가')
    Discount_Rate = Column(Float, default=0.0, comment='할인율')
    Margin = Column(Integer, comment='마진')
    Margin_Rate = Column(Float, comment='마진율')
    Validity_Period = Column(Integer, comment='유효기간 (일)')

    # 관계 설정
    procedure_info = relationship("ProcedureInfo", back_populates="procedure_products")

    __table_args__ = (
        Index('idx_package_type', 'Package_Type'),
        Index('idx_procedure_id', 'Procedure_ID'),
        Index('idx_release', 'Release'),
        {'mysql_engine': 'InnoDB'},
    )

    def __repr__(self):
        return f"<ProcedureProduct(ID={self.ID}, Package_Type='{self.Package_Type}', Price={self.Price})>"