"""
    삭제 기능 공통 기반
    
    이 모듈은 모든 삭제 기능의 기본 클래스와 공통 모델을 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# ============================================================================
# 공통 모델
# ============================================================================

class DeletionSeverity(str, Enum):
    """삭제 위험도 수준"""
    SAFE = "safe"        # 안전 - 삭제 가능
    WARNING = "warning"   # 경고 - 주의 필요
    DANGER = "danger"     # 위험 - 삭제 불가

class ReferenceInfo(BaseModel):
    """참조 정보 상세"""
    table_name: str
    item_id: int
    item_name: Optional[str] = None
    item_type: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None

class ReferenceSummary(BaseModel):
    """참조 정보 요약"""
    total_references: int = 0
    critical_references: int = 0  # 상품 등 중요한 참조
    tables_affected: List[str] = []
    severity_level: DeletionSeverity = DeletionSeverity.SAFE

class DeletionResult(BaseModel):
    """삭제 검증 결과"""
    item_id: int
    item_type: str
    is_deletable: bool
    severity: DeletionSeverity
    message: str
    references: Dict[str, Any] = {}
    summary: ReferenceSummary
    recommendations: List[str] = []
    
    class Config:
        from_attributes = True

class DeletionResponse(BaseModel):
    """삭제 API 응답"""
    status: str
    message: str
    data: DeletionResult

# ============================================================================
# 공통 기반 클래스
# ============================================================================

class BaseDeletionValidator(ABC):
    """삭제 검증 기본 클래스"""
    
    def __init__(self):
        self.item_type = self.__class__.__name__.replace("DeletionValidator", "").lower()
    
    @abstractmethod
    def validate_deletion(self, item_id: int, db: Session) -> DeletionResult:
        """
        삭제 안전성 검증
        
        Args:
            item_id: 삭제하려는 항목 ID
            db: 데이터베이스 세션
        
        Returns:
            DeletionResult: 삭제 검증 결과
        """
        pass
    
    @abstractmethod
    def execute_deletion(self, item_id: int, db: Session, force: bool = False) -> bool:
        """
        삭제 실행
        
        Args:
            item_id: 삭제하려는 항목 ID
            db: 데이터베이스 세션
            force: 강제 삭제 여부
        
        Returns:
            bool: 삭제 성공 여부
        """
        pass
    
    def _determine_severity(self, references: Dict[str, Any]) -> DeletionSeverity:
        """참조 정보를 바탕으로 위험도 결정"""
        if not references or references.get("total_references", 0) == 0:
            return DeletionSeverity.SAFE
        
        critical_count = references.get("critical_references", 0)
        total_count = references.get("total_references", 0)
        
        if critical_count > 0:
            return DeletionSeverity.DANGER
        elif total_count > 0:
            return DeletionSeverity.WARNING
        
        return DeletionSeverity.SAFE
    
    def _generate_message(self, references: Dict[str, Any], item_type: str) -> str:
        """참조 정보를 바탕으로 사용자 메시지 생성"""
        if not references or references.get("total_references", 0) == 0:
            return f"이 {item_type}는 안전하게 삭제할 수 있습니다."
        
        total_refs = references.get("total_references", 0)
        critical_refs = references.get("critical_references", 0)
        
        if critical_refs > 0:
            return f"이 {item_type}는 삭제할 수 없습니다. {critical_refs}개의 중요한 항목에서 사용 중입니다."
        else:
            return f"이 {item_type}는 삭제할 수 없습니다. {total_refs}개의 항목에서 사용 중입니다."
    
    def _generate_recommendations(self, references: Dict[str, Any], item_type: str) -> List[str]:
        """참조 정보를 바탕으로 권장사항 생성"""
        recommendations = []
        
        if references.get("products"):
            recommendations.append(f"먼저 이 {item_type}를 사용하는 상품들을 삭제하거나 수정하세요.")
        
        if references.get("bundles"):
            recommendations.append(f"Bundle 시술에서 이 {item_type}를 제거하세요.")
        
        if references.get("customs"):
            recommendations.append(f"Custom 시술에서 이 {item_type}를 제거하세요.")
        
        if references.get("sequences"):
            recommendations.append(f"Sequence 시술에서 이 {item_type}를 제거하세요.")
        
        if not recommendations:
            recommendations.append(f"참조 관계를 확인한 후 단계적으로 제거하세요.")
        
        return recommendations
