"""
    Bundle 삭제 기능
    
    이 모듈은 Bundle의 삭제 전 안전성 검증과 삭제 실행을 담당합니다.
    Bundle 삭제 시 시퀀스에서의 참조도 고려합니다.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .base import BaseDeletionValidator, DeletionResult, DeletionSeverity, ReferenceSummary
from db.models.procedure import ProcedureBundle
from db.models.product import ProductStandard, ProductEvent
from db.models.procedure import ProcedureSequence

class BundleDeletionValidator(BaseDeletionValidator):
    """Bundle 삭제 검증 및 실행"""
    
    def __init__(self):
        super().__init__()
        self.item_type = "bundle"
    
    def validate_deletion(self, bundle_id: int, db: Session) -> DeletionResult:
        """
        Bundle 삭제 안전성 검증
        
        Args:
            bundle_id: 삭제하려는 Bundle GroupID
            db: 데이터베이스 세션
        
        Returns:
            DeletionResult: 삭제 검증 결과
        """
        
        # 1. Bundle 존재 여부 확인
        bundles = db.query(ProcedureBundle).filter(
            ProcedureBundle.GroupID == bundle_id
        ).all()
        
        if not bundles:
            raise ValueError(f"Bundle GroupID {bundle_id}를 찾을 수 없습니다.")
        
        # 2. 참조 관계 조회
        references = self._get_references(bundle_id, db)
        
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
            item_id=bundle_id,
            item_type=self.item_type,
            is_deletable=is_deletable,
            severity=severity,
            message=message,
            references=references,
            summary=summary,
            recommendations=recommendations
        )
    
    def execute_deletion(self, bundle_id: int, db: Session, force: bool = False) -> bool:
        """
        Bundle 삭제 실행
        
        Args:
            bundle_id: 삭제하려는 Bundle GroupID
            db: 데이터베이스 세션
            force: 강제 삭제 여부
        
        Returns:
            bool: 삭제 성공 여부
        """
        
        try:
            # 1. 강제 삭제가 아닌 경우 안전성 검증
            if not force:
                result = self.validate_deletion(bundle_id, db)
                if not result.is_deletable:
                    raise ValueError(f"Bundle을 삭제할 수 없습니다: {result.message}")
            
            # 2. Bundle 조회 (GroupID로 모든 Bundle 가져오기)
            bundles = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == bundle_id
            ).all()
            
            if not bundles:
                raise ValueError(f"Bundle GroupID {bundle_id}를 찾을 수 없습니다.")
            
            # 3. 모든 Bundle 삭제 (GroupID가 같은 모든 Bundle)
            for bundle in bundles:
                db.delete(bundle)
            
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            raise e
    
    def _get_references(self, bundle_id: int, db: Session) -> Dict[str, Any]:
        """
        Bundle이 참조되는 모든 곳 조회
        
        Args:
            bundle_id: Bundle GroupID
            db: 데이터베이스 세션
        
        Returns:
            Dict: 참조 정보
        """
        
        references = {
            "products": [],
            "sequences": [],
            "total_references": 0,
            "critical_references": 0,
            "tables_affected": []
        }
        
        # 1. Product에서 참조 확인 (가장 중요 - critical)
        standard_products = db.query(ProductStandard).filter(
            ProductStandard.Bundle_ID == bundle_id
        ).all()
        
        event_products = db.query(ProductEvent).filter(
            ProductEvent.Bundle_ID == bundle_id
        ).all()
        
        if standard_products:
            references["products"].extend([
                {
                    "table": "Product_Standard",
                    "id": p.ID,
                    "type": "Standard 상품",
                    "sell_price": p.Sell_Price,
                    "package_type": p.Package_Type
                }
                for p in standard_products
            ])
            references["tables_affected"].append("Product_Standard")
        
        if event_products:
            references["products"].extend([
                {
                    "table": "Product_Event",
                    "id": p.ID,
                    "type": "Event 상품",
                    "sell_price": p.Sell_Price,
                    "package_type": p.Package_Type
                }
                for p in event_products
            ])
            references["tables_affected"].append("Product_Event")
        
        # 2. Sequence에서 참조 확인 (중요 - 시퀀스 내부에서 Bundle 사용)
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.Bundle_ID == bundle_id
        ).all()
        
        if sequences:
            references["sequences"].extend([
                {
                    "id": s.ID,
                    "name": s.Name,
                    "group_id": s.GroupID,
                    "step_num": s.Step_Num,
                    "context": f"시퀀스 {s.GroupID}의 {s.Step_Num}단계"
                }
                for s in sequences
            ])
            references["tables_affected"].append("Procedure_Sequence")
        
        # 3. 요약 정보 계산
        references["total_references"] = (
            len(references["products"]) + 
            len(references["sequences"])
        )
        
        references["critical_references"] = len(references["products"])
        
        # 4. 중복 제거
        references["tables_affected"] = list(set(references["tables_affected"]))
        
        return references
