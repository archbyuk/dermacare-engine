"""
    Element 삭제 기능
    
    이 모듈은 Element의 삭제 전 안전성 검증과 삭제 실행을 담당합니다.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .base import BaseDeletionValidator, DeletionResult, DeletionSeverity, ReferenceSummary
from db.models.procedure import ProcedureElement
from db.models.product import ProductStandard, ProductEvent
from db.models.procedure import ProcedureBundle, ProcedureCustom, ProcedureSequence

class ElementDeletionValidator(BaseDeletionValidator):
    """Element 삭제 검증 및 실행"""
    
    def __init__(self):
        super().__init__()
        self.item_type = "element"
    
    def validate_deletion(self, element_id: int, db: Session) -> DeletionResult:
        """
        Element 삭제 안전성 검증
        
        Args:
            element_id: 삭제하려는 Element ID
            db: 데이터베이스 세션
        
        Returns:
            DeletionResult: 삭제 검증 결과
        """
        
        # 1. Element 존재 여부 확인
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id
        ).first()
        
        if not element:
            raise ValueError(f"Element ID {element_id}를 찾을 수 없습니다.")
        
        # 2. 참조 관계 조회
        references = self._get_references(element_id, db)
        
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
            item_id=element_id,
            item_type=self.item_type,
            is_deletable=is_deletable,
            severity=severity,
            message=message,
            references=references,
            summary=summary,
            recommendations=recommendations
        )
    
    def execute_deletion(self, element_id: int, db: Session, force: bool = False) -> bool:
        """
        Element 삭제 실행
        
        Args:
            element_id: 삭제하려는 Element ID
            db: 데이터베이스 세션
            force: 강제 삭제 여부
        
        Returns:
            bool: 삭제 성공 여부
        """
        
        try:
            # 1. 강제 삭제가 아닌 경우 안전성 검증
            if not force:
                result = self.validate_deletion(element_id, db)
                if not result.is_deletable:
                    raise ValueError(f"Element를 삭제할 수 없습니다: {result.message}")
            
            # 2. Element 조회
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == element_id
            ).first()
            
            if not element:
                raise ValueError(f"Element ID {element_id}를 찾을 수 없습니다.")
            
            # 3. 삭제 실행
            db.delete(element)
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            raise e
    
    def _get_references(self, element_id: int, db: Session) -> Dict[str, Any]:
        """
        Element가 참조되는 모든 곳 조회
        
        Args:
            element_id: Element ID
            db: 데이터베이스 세션
        
        Returns:
            Dict: 참조 정보
        """
        
        references = {
            "products": [],
            "bundles": [],
            "customs": [],
            "sequences": [],
            "total_references": 0,
            "critical_references": 0,
            "tables_affected": []
        }
        
        # 1. Product에서 참조 확인 (가장 중요 - critical)
        standard_products = db.query(ProductStandard).filter(
            ProductStandard.Element_ID == element_id
        ).all()
        
        event_products = db.query(ProductEvent).filter(
            ProductEvent.Element_ID == element_id
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
        
        # 2. Bundle에서 참조 확인
        bundles = db.query(ProcedureBundle).filter(
            ProcedureBundle.Element_ID == element_id
        ).all()
        
        if bundles:
            references["bundles"].extend([
                {
                    "id": b.ID,
                    "name": b.Name,
                    "group_id": b.GroupID,
                    "element_cost": b.Element_Cost
                }
                for b in bundles
            ])
            references["tables_affected"].append("Procedure_Bundle")
        
        # 3. Custom에서 참조 확인
        customs = db.query(ProcedureCustom).filter(
            ProcedureCustom.Element_ID == element_id
        ).all()
        
        if customs:
            references["customs"].extend([
                {
                    "id": c.ID,
                    "name": c.Name,
                    "group_id": c.GroupID,
                    "element_cost": c.Element_Cost
                }
                for c in customs
            ])
            references["tables_affected"].append("Procedure_Custom")
        
        # 4. Sequence에서 참조 확인
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.Element_ID == element_id
        ).all()
        
        if sequences:
            references["sequences"].extend([
                {
                    "id": s.ID,
                    "name": s.Name,
                    "group_id": s.GroupID,
                    "step_num": s.Step_Num
                }
                for s in sequences
            ])
            references["tables_affected"].append("Procedure_Sequence")
        
        # 5. 요약 정보 계산
        references["total_references"] = (
            len(references["products"]) + 
            len(references["bundles"]) + 
            len(references["customs"]) + 
            len(references["sequences"])
        )
        
        references["critical_references"] = len(references["products"])
        
        # 6. 중복 제거
        references["tables_affected"] = list(set(references["tables_affected"]))
        
        return references
