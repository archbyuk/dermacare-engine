"""
    Sequence 삭제 기능
    
    이 모듈은 Sequence의 삭제 전 안전성 검증과 삭제 실행을 담당합니다.
    Sequence 삭제 시 내부에서 참조하는 Element, Bundle, Custom도 고려합니다.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .base import BaseDeletionValidator, DeletionResult, DeletionSeverity, ReferenceSummary
from db.models.procedure import ProcedureSequence
from db.models.product import ProductStandard, ProductEvent
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom

class SequenceDeletionValidator(BaseDeletionValidator):
    """Sequence 삭제 검증 및 실행"""
    
    def __init__(self):
        super().__init__()
        self.item_type = "sequence"
    
    def validate_deletion(self, sequence_id: int, db: Session) -> DeletionResult:
        """
        Sequence 삭제 안전성 검증
        
        Args:
            sequence_id: 삭제하려는 Sequence GroupID
            db: 데이터베이스 세션
        
        Returns:
            DeletionResult: 삭제 검증 결과
        """
        
        # 1. Sequence 존재 여부 확인
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.GroupID == sequence_id
        ).all()
        
        if not sequences:
            raise ValueError(f"Sequence GroupID {sequence_id}를 찾을 수 없습니다.")
        
        # 2. 참조 관계 조회
        references = self._get_references(sequence_id, db)
        
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
            item_id=sequence_id,
            item_type=self.item_type,
            is_deletable=is_deletable,
            severity=severity,
            message=message,
            references=references,
            summary=summary,
            recommendations=recommendations
        )
    
    def execute_deletion(self, sequence_id: int, db: Session, force: bool = False) -> bool:
        """
        Sequence 삭제 실행
        
        Args:
            sequence_id: 삭제하려는 Sequence GroupID
            db: 데이터베이스 세션
            force: 강제 삭제 여부
        
        Returns:
            bool: 삭제 성공 여부
        """
        
        try:
            # 1. 강제 삭제가 아닌 경우 안전성 검증
            if not force:
                result = self.validate_deletion(sequence_id, db)
                if not result.is_deletable:
                    raise ValueError(f"Sequence를 삭제할 수 없습니다: {result.message}")
            
            # 2. Sequence 조회 (GroupID로 모든 Sequence 가져오기)
            sequences = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID == sequence_id
            ).all()
            
            if not sequences:
                raise ValueError(f"Sequence GroupID {sequence_id}를 찾을 수 없습니다.")
            
            # 3. 모든 Sequence 삭제 (GroupID가 같은 모든 Sequence)
            for sequence in sequences:
                db.delete(sequence)
            
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            raise e
    
    def _get_references(self, sequence_id: int, db: Session) -> Dict[str, Any]:
        """
        Sequence가 참조되는 모든 곳 조회
        
        Args:
            sequence_id: Sequence GroupID
            db: 데이터베이스 세션
        
        Returns:
            Dict: 참조 정보
        """
        
        references = {
            "products": [],
            "internal_elements": [],
            "internal_bundles": [],
            "internal_customs": [],
            "total_references": 0,
            "critical_references": 0,
            "tables_affected": []
        }
        
        # 1. Product에서 참조 확인 (가장 중요 - critical)
        standard_products = db.query(ProductStandard).filter(
            ProductStandard.Sequence_ID == sequence_id
        ).all()
        
        event_products = db.query(ProductEvent).filter(
            ProductEvent.Sequence_ID == sequence_id
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
        
        # 2. Sequence 내부에서 참조하는 Element 확인
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.GroupID == sequence_id
        ).all()
        
        for sequence in sequences:
            # Element 참조
            if sequence.Element_ID:
                element = db.query(ProcedureElement).filter(
                    ProcedureElement.ID == sequence.Element_ID
                ).first()
                if element:
                    references["internal_elements"].append({
                        "id": element.ID,
                        "name": element.Name,
                        "step_num": sequence.Step_Num,
                        "context": f"시퀀스 {sequence_id}의 {sequence.Step_Num}단계"
                    })
            
            # Bundle 참조
            if sequence.Bundle_ID:
                bundle = db.query(ProcedureBundle).filter(
                    ProcedureBundle.GroupID == sequence.Bundle_ID
                ).first()
                if bundle:
                    references["internal_bundles"].append({
                        "id": bundle.GroupID,
                        "name": bundle.Name,
                        "step_num": sequence.Step_Num,
                        "context": f"시퀀스 {sequence_id}의 {sequence.Step_Num}단계"
                    })
            
            # Custom 참조
            if sequence.Custom_ID:
                custom = db.query(ProcedureCustom).filter(
                    ProcedureCustom.GroupID == sequence.Custom_ID
                ).first()
                if custom:
                    references["internal_customs"].append({
                        "id": custom.GroupID,
                        "name": custom.Name,
                        "step_num": sequence.Step_Num,
                        "context": f"시퀀스 {sequence_id}의 {sequence.Step_Num}단계"
                    })
        
        # 3. 요약 정보 계산
        references["total_references"] = (
            len(references["products"]) + 
            len(references["internal_elements"]) + 
            len(references["internal_bundles"]) + 
            len(references["internal_customs"])
        )
        
        references["critical_references"] = len(references["products"])
        
        # 4. 중복 제거
        references["tables_affected"] = list(set(references["tables_affected"]))
        
        return references
