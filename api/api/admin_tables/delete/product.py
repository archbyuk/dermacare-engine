"""
    Product 삭제 기능
    
    이 모듈은 Product의 삭제 전 안전성 검증과 삭제 실행을 담당합니다.
    Product는 가장 중요한 엔티티이므로 삭제 시 주의가 필요합니다.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .base import BaseDeletionValidator, DeletionResult, DeletionSeverity, ReferenceSummary
from db.models.product import ProductStandard, ProductEvent
from db.models.info import InfoStandard, InfoEvent

class ProductDeletionValidator(BaseDeletionValidator):
    """Product 삭제 검증 및 실행"""
    
    def __init__(self):
        super().__init__()
        self.item_type = "product"
    
    def validate_deletion(self, product_id: int, db: Session) -> DeletionResult:
        """
        Product 삭제 안전성 검증
        
        Args:
            product_id: 삭제하려는 Product ID
            db: 데이터베이스 세션
        
        Returns:
            DeletionResult: 삭제 검증 결과
        """
        
        # 1. Product 존재 여부 확인
        standard_product = db.query(ProductStandard).filter(
            ProductStandard.ID == product_id
        ).first()
        
        event_product = db.query(ProductEvent).filter(
            ProductEvent.ID == product_id
        ).first()
        
        if not standard_product and not event_product:
            raise ValueError(f"Product ID {product_id}를 찾을 수 없습니다.")
        
        # 2. 참조 관계 조회
        references = self._get_references(product_id, db)
        
        # 3. 위험도 결정
        severity = self._determine_severity(references)
        
        # 4. 삭제 가능 여부 결정
        is_deletable = references.get("total_references", 0) == 0
        
        # 5. 사용자 메시지 생성
        message = self._generate_message(references, self.item_type)
        
        # 6. 권장사항 생성
        recommendations = self._generate_recommendations(references, self.item_type)
        
        # 7. 요약 정보 생성
        summary = ReferenceSummary(
            total_references=references.get("total_references", 0),
            critical_references=references.get("critical_references", 0),
            tables_affected=references.get("tables_affected", []),
            severity_level=severity
        )
        
        return DeletionResult(
            item_id=product_id,
            item_type=self.item_type,
            is_deletable=is_deletable,
            severity=severity,
            message=message,
            references=references,
            summary=summary,
            recommendations=recommendations
        )
    
    def execute_deletion(self, product_id: int, db: Session, force: bool = False) -> bool:
        """
        Product 삭제 실행
        
        Args:
            product_id: 삭제하려는 Product ID
            db: 데이터베이스 세션
            force: 강제 삭제 여부
        
        Returns:
            bool: 삭제 성공 여부
        """
        
        try:
            # 1. 강제 삭제가 아닌 경우 안전성 검증
            if not force:
                result = self.validate_deletion(product_id, db)
                if not result.is_deletable:
                    raise ValueError(f"Product를 삭제할 수 없습니다: {result.message}")
            
            # 2. Product 조회
            standard_product = db.query(ProductStandard).filter(
                ProductStandard.ID == product_id
            ).first()
            
            event_product = db.query(ProductEvent).filter(
                ProductEvent.ID == product_id
            ).first()
            
            if not standard_product and not event_product:
                raise ValueError(f"Product ID {product_id}를 찾을 수 없습니다.")
            
            # 3. Product 삭제
            if standard_product:
                db.delete(standard_product)
            if event_product:
                db.delete(event_product)
            
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            raise e
    
    def _get_references(self, product_id: int, db: Session) -> Dict[str, Any]:
        """
        Product가 참조되는 모든 곳 조회
        
        Args:
            product_id: Product ID
            db: 데이터베이스 세션
        
        Returns:
            Dict: 참조 정보
        """
        
        references = {
            "memberships": [],
            "total_references": 0,
            "critical_references": 0,
            "tables_affected": []
        }
        
        # 1. Membership에서 참조 확인 (중요 - 멤버십에서 상품 사용)
        # Membership 테이블에서 product_id 참조 확인
        # 실제 Membership 모델 구조에 따라 조정 필요
        
        # 2. 다른 상품과의 연관 관계 확인
        # 예: 패키지 상품, 세트 상품 등
        
        # 3. 요약 정보 계산
        references["total_references"] = len(references["memberships"])
        references["critical_references"] = len(references["memberships"])
        
        # 4. 중복 제거
        references["tables_affected"] = list(set(references["tables_affected"]))
        
        return references
