"""
    Membership 삭제 기능
    
    이 모듈은 Membership의 삭제 전 안전성 검증과 삭제 실행을 담당합니다.
    Membership은 고객과 관련된 중요한 엔티티입니다.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .base import BaseDeletionValidator, DeletionResult, DeletionSeverity, ReferenceSummary
from db.models.membership import Membership
from db.models.info import InfoMembership

class MembershipDeletionValidator(BaseDeletionValidator):
    """Membership 삭제 검증 및 실행"""
    
    def __init__(self):
        super().__init__()
        self.item_type = "membership"
    
    def validate_deletion(self, membership_id: int, db: Session) -> DeletionResult:
        """
        Membership 삭제 안전성 검증
        
        Args:
            membership_id: 삭제하려는 Membership ID
            db: 데이터베이스 세션
        
        Returns:
            DeletionResult: 삭제 검증 결과
        """
        
        # 1. Membership 존재 여부 확인
        membership = db.query(Membership).filter(
            Membership.ID == membership_id
        ).first()
        
        if not membership:
            raise ValueError(f"Membership ID {membership_id}를 찾을 수 없습니다.")
        
        # 2. 참조 관계 조회
        references = self._get_references(membership_id, db)
        
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
            item_id=membership_id,
            item_type=self.item_type,
            is_deletable=is_deletable,
            severity=severity,
            message=message,
            references=references,
            summary=summary,
            recommendations=recommendations
        )
    
    def execute_deletion(self, membership_id: int, db: Session, force: bool = False) -> bool:
        """
        Membership 삭제 실행
        
        Args:
            membership_id: 삭제하려는 Membership ID
            db: 데이터베이스 세션
            force: 강제 삭제 여부
        
        Returns:
            bool: 삭제 성공 여부
        """
        
        try:
            # 1. 강제 삭제가 아닌 경우 안전성 검증
            if not force:
                result = self.validate_deletion(membership_id, db)
                if not result.is_deletable:
                    raise ValueError(f"Membership을 삭제할 수 없습니다: {result.message}")
            
            # 2. Membership 조회
            membership = db.query(Membership).filter(
                Membership.ID == membership_id
            ).first()
            
            if not membership:
                raise ValueError(f"Membership ID {membership_id}를 찾을 수 없습니다.")
            
            # 3. Membership 삭제
            db.delete(membership)
            
            # 4. 관련 InfoMembership도 함께 삭제 (선택사항)
            # 만약 다른 곳에서 사용되지 않는다면
            info_membership = db.query(InfoMembership).filter(
                InfoMembership.ID == membership.Membership_Info_ID
            ).first()
            
            if info_membership:
                # 다른 Membership에서 사용하지 않는지 확인
                other_memberships = db.query(Membership).filter(
                    Membership.Membership_Info_ID == membership.Membership_Info_ID,
                    Membership.ID != membership_id
                ).count()
                
                if other_memberships == 0:
                    db.delete(info_membership)
            
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            raise e
    
    def _get_references(self, membership_id: int, db: Session) -> Dict[str, Any]:
        """
        Membership이 참조되는 모든 곳 조회
        
        Args:
            membership_id: Membership ID
            db: 데이터베이스 세션
        
        Returns:
            Dict: 참조 정보
        """
        
        references = {
            "customers": [],
            "orders": [],
            "total_references": 0,
            "critical_references": 0,
            "tables_affected": []
        }
        
        # 1. 고객 정보에서 참조 확인 (중요 - 고객 멤버십)
        # Customer 테이블에서 membership_id 참조 확인
        # 실제 Customer 모델 구조에 따라 조정 필요
        
        # 2. 주문 정보에서 참조 확인 (중요 - 멤버십 할인 적용)
        # Order 테이블에서 membership_id 참조 확인
        # 실제 Order 모델 구조에 따라 조정 필요
        
        # 3. 요약 정보 계산
        references["total_references"] = (
            len(references["customers"]) + 
            len(references["orders"])
        )
        
        references["critical_references"] = (
            len(references["customers"]) + 
            len(references["orders"])
        )
        
        # 4. 중복 제거
        references["tables_affected"] = list(set(references["tables_affected"]))
        
        return references
