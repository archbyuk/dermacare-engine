"""
    삭제 기능 공통 유틸리티
    
    이 모듈은 삭제 기능에서 사용하는 공통 유틸리티 함수들을 제공합니다.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

def format_reference_info(references: Dict[str, Any]) -> str:
    """
    참조 정보를 사용자 친화적인 문자열로 포맷팅
    
    Args:
        references: 참조 정보 딕셔너리
    
    Returns:
        str: 포맷팅된 문자열
    """
    
    if not references or references.get("total_references", 0) == 0:
        return "참조되는 곳이 없습니다."
    
    parts = []
    
    # 상품 정보
    if references.get("products"):
        product_count = len(references["products"])
        parts.append(f"상품: {product_count}개")
    
    # Bundle 정보
    if references.get("bundles"):
        bundle_count = len(references["bundles"])
        parts.append(f"번들: {bundle_count}개")
    
    # Custom 정보
    if references.get("customs"):
        custom_count = len(references["customs"])
        parts.append(f"커스텀: {custom_count}개")
    
    # Sequence 정보
    if references.get("sequences"):
        sequence_count = len(references["sequences"])
        parts.append(f"시퀀스: {sequence_count}개")
    
    return ", ".join(parts)

def get_table_display_name(table_name: str) -> str:
    """
    테이블명을 사용자 친화적인 이름으로 변환
    
    Args:
        table_name: 데이터베이스 테이블명
    
    Returns:
        str: 사용자 친화적인 이름
    """
    
    table_names = {
        "Product_Standard": "Standard 상품",
        "Product_Event": "Event 상품",
        "Procedure_Bundle": "번들 시술",
        "Procedure_Custom": "커스텀 시술",
        "Procedure_Sequence": "시퀀스 시술",
        "Procedure_Element": "단일 시술",
        "Info_Standard": "Standard 정보",
        "Info_Event": "Event 정보",
        "Info_Membership": "멤버십 정보",
        "Membership": "멤버십"
    }
    
    return table_names.get(table_name, table_name)

def create_deletion_summary(references: Dict[str, Any]) -> Dict[str, Any]:
    """
    참조 정보를 바탕으로 삭제 요약 정보 생성
    
    Args:
        references: 참조 정보
    
    Returns:
        Dict: 요약 정보
    """
    
    summary = {
        "total_references": references.get("total_references", 0),
        "critical_references": references.get("critical_references", 0),
        "tables_affected": references.get("tables_affected", []),
        "can_delete": references.get("total_references", 0) == 0,
        "risk_level": "low"
    }
    
    # 위험도 결정
    if summary["critical_references"] > 0:
        summary["risk_level"] = "high"
    elif summary["total_references"] > 0:
        summary["risk_level"] = "medium"
    
    return summary

def validate_item_exists(item_type: str, item_id: int, db: Session) -> bool:
    """
    항목이 데이터베이스에 존재하는지 검증
    
    Args:
        item_type: 항목 타입
        item_id: 항목 ID
        db: 데이터베이스 세션
    
    Returns:
        bool: 존재 여부
    """
    
    try:
        # 동적 테이블명 생성
        table_name = f"Procedure_{item_type.capitalize()}"
        
        # SQL 쿼리 실행
        query = text(f"SELECT COUNT(*) FROM {table_name} WHERE ID = :item_id")
        result = db.execute(query, {"item_id": item_id})
        count = result.scalar()
        
        return count > 0
        
    except Exception:
        return False

def get_reference_details(references: Dict[str, Any], max_items: int = 5) -> Dict[str, Any]:
    """
    참조 정보의 상세 내용을 제한된 개수로 반환
    
    Args:
        references: 참조 정보
        max_items: 최대 표시할 항목 개수
    
    Returns:
        Dict: 제한된 참조 정보
    """
    
    limited_references = {}
    
    for key, items in references.items():
        if isinstance(items, list):
            limited_references[key] = items[:max_items]
            if len(items) > max_items:
                limited_references[f"{key}_overflow"] = len(items) - max_items
        else:
            limited_references[key] = items
    
    return limited_references

def generate_deletion_warning(references: Dict[str, Any], item_type: str) -> str:
    """
    삭제 경고 메시지 생성
    
    Args:
        references: 참조 정보
        item_type: 삭제하려는 항목 타입
    
    Returns:
        str: 경고 메시지
    """
    
    if not references or references.get("total_references", 0) == 0:
        return f"이 {item_type}는 안전하게 삭제할 수 있습니다."
    
    total_refs = references.get("total_references", 0)
    critical_refs = references.get("critical_references", 0)
    
    if critical_refs > 0:
        return f"⚠️ 주의: 이 {item_type}는 {critical_refs}개의 상품에서 사용 중입니다. 삭제할 수 없습니다."
    else:
        return f"⚠️ 경고: 이 {item_type}는 {total_refs}개의 항목에서 사용 중입니다. 삭제 시 주의가 필요합니다."
