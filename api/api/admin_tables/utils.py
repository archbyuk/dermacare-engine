"""
    관리자용 테이블 API 유틸리티 함수들
    
    이 모듈은 연쇄 업데이트, 가격 계산, 벌크 업데이트 등의 유틸리티 함수들을 제공합니다.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any

from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence
from db.models.product import ProductEvent, ProductStandard
from db.models.global_config import Global
from db.models.consumables import Consumables
from db.models.info import InfoMembership

# ============================================================================
# 가격 계산 함수들
# ============================================================================

def calculate_unit_price(price: int, i_value: int, f_value: float) -> int:
    """
    Consumable의 Unit_Price 계산
    
    공식: ROUNDDOWN(Price / IF(I_Value <> -1, I_Value, F_Value), 0)
    """
    try:
        if i_value is not None and i_value != -1:
            divisor = i_value
        else:
            divisor = f_value
        
        if divisor == 0:
            return 0
        # 둘 다 존재하거나 둘 다 nono일때 예외처리 필요
        unit_price = price / divisor
        return int(unit_price)  # ROUNDDOWN 효과
    except Exception as e:
        print(f"Unit_Price 계산 중 오류: {str(e)}")
        return 0

def calculate_vat(unit_price: int, taxable_type: str) -> int:
    """
    Consumable의 VAT 계산
    
    공식: IF(TaxableType="과세", Unit_Price/11, 0)
    """
    try:
        print(f"VAT 계산 디버깅: unit_price={unit_price}, taxable_type='{taxable_type}', len={len(taxable_type) if taxable_type else 0}")
        if taxable_type == "과세":
            vat = int(unit_price / 11)
            print(f"VAT 계산 결과: {vat}")
            return vat
        else:
            print(f"VAT 계산 결과: 0 (과세가 아님)")
            return 0
    except Exception as e:
        print(f"VAT 계산 중 오류: {str(e)}")
        return 0

def calculate_element_procedure_cost(
    position_type: str,
    cost_time: float,
    consum_1_id: int,
    consum_1_count: int,
    plan_state: int,
    plan_count: int,
    global_settings: Global,
    consumable: Consumables = None
) -> int:
    """
    Element의 Procedure_Cost 계산 (통일된 버전)
    
    Excel 수식: =(IF(K5<>"의사",([Global.xlsx]Global!$B$5*L5),([Global.xlsx]Global!$C$5*L5))+(IF(P5<>-1,XLOOKUP(P5,[Consumables.xlsx]Consumables!$A:$A,[Consumables.xlsx]Consumables!$K:$K,0),0)*(IF(R5<>-1,R5,1))))*(IF(M5<>0,N5,1))
    
    Args:
        position_type: Position_Type (의사/관리사)
        cost_time: Cost_Time (소요시간)
        consum_1_id: Consum_1_ID (소모품 ID)
        consum_1_count: Consum_1_Count (소모품 개수)
        plan_state: Plan_State (플랜 여부)
        plan_count: Plan_Count (플랜 배수)
        global_settings: Global 설정
        consumable: Consumable 객체 (선택적)
    
    Returns:
        int: 계산된 Procedure_Cost
    """
    try:
        # 1. 인건비 계산
        if position_type != "의사":
            # 관리사 인건비
            labor_cost = global_settings.Aesthetician_Price_Minute * cost_time
        else:
            # 의사 인건비
            labor_cost = global_settings.Doc_Price_Minute * cost_time
        
        # 2. 소모품비용 계산
        consumable_cost = 0
        if consum_1_id != -1 and consumable:
            unit_price = consumable.Unit_Price or 0
            count = consum_1_count if consum_1_count != -1 else 1
            consumable_cost = unit_price * count
        
        # 3. 총 원가 계산
        total_cost = labor_cost + consumable_cost
        
        # 4. 플랜 배수 적용 (IF(M5<>0,N5,1))
        if plan_state != 0:
            total_cost *= plan_count
        
        return int(total_cost)
    except Exception as e:
        print(f"Element Procedure_Cost 계산 중 오류: {str(e)}")
        return 0

def calculate_element_procedure_cost_from_element(
    element: ProcedureElement,
    global_settings: Global,
    consumable: Consumables = None
) -> int:
    """
    Element 객체로부터 Procedure_Cost 계산 (헬퍼 함수)
    """
    return calculate_element_procedure_cost(
        element.Position_Type or "",
        element.Cost_Time or 0,
        element.Consum_1_ID or -1,
        element.Consum_1_Count or 1,
        element.Plan_State or 0,
        element.Plan_Count or 1,
        global_settings,
        consumable
    )

# ============================================================================
# 벌크 업데이트 함수들
# ============================================================================

def bulk_update_element_procedure_costs(db: Session, global_settings: Global) -> int:
    """
    모든 Element의 Procedure_Cost를 벌크 업데이트
    
    Returns:
        int: 업데이트된 Element 수
    """
    try:
        # 모든 활성화된 Element 조회
        elements = db.query(ProcedureElement).filter(ProcedureElement.Release == 1).all()
        
        # 각 Element의 Procedure_Cost 재계산
        for element in elements:
            # 해당 Element가 사용하는 Consumable 조회
            consumable = None
            if element.Consum_1_ID:
                consumable = db.query(Consumables).filter(
                    Consumables.ID == element.Consum_1_ID,
                    Consumables.Release == 1
                ).first()
            
            # Procedure_Cost 재계산 (통일된 함수 사용)
            new_cost = calculate_element_procedure_cost_from_element(element, global_settings, consumable)
            element.Procedure_Cost = new_cost
        
        db.commit()
        return len(elements)
    except Exception as e:
        db.rollback()
        print(f"Element Procedure_Cost 벌크 업데이트 중 오류: {str(e)}")
        raise

def bulk_update_referenced_element_costs(db: Session) -> Dict[str, int]:
    """
    Bundle과 Custom의 Element_Cost를 벌크 업데이트 (통일된 함수)
    
    Returns:
        Dict[str, int]: Bundle과 Custom 업데이트 수
    """
    try:
        results = {}
        
        # Bundle Element_Cost 업데이트
        bundles = db.query(ProcedureBundle).filter(ProcedureBundle.Release == 1).all()
        for bundle in bundles:
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == bundle.Element_ID,
                ProcedureElement.Release == 1
            ).first()
            if element:
                bundle.Element_Cost = element.Procedure_Cost
        results['bundles'] = len(bundles)
        
        # Custom Element_Cost 업데이트
        customs = db.query(ProcedureCustom).filter(ProcedureCustom.Release == 1).all()
        for custom in customs:
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == custom.Element_ID,
                ProcedureElement.Release == 1
            ).first()
            if element:
                custom.Element_Cost = element.Procedure_Cost
        results['customs'] = len(customs)
        
        db.commit()
        return results
    except Exception as e:
        db.rollback()
        print(f"Bundle/Custom Element_Cost 벌크 업데이트 중 오류: {str(e)}")
        raise

# 기존 함수들 호환성을 위해 유지 (내부적으로 통일된 함수 사용)
def bulk_update_bundle_element_costs(db: Session) -> int:
    """모든 Bundle의 Element_Cost를 벌크 업데이트"""
    results = bulk_update_referenced_element_costs(db)
    return results['bundles']

def bulk_update_custom_element_costs(db: Session) -> int:
    """모든 Custom의 Element_Cost를 벌크 업데이트"""
    results = bulk_update_referenced_element_costs(db)
    return results['customs']

def bulk_update_sequence_procedure_costs(db: Session) -> int:
    """
    모든 Sequence의 Procedure_Cost를 벌크 업데이트
    
    Returns:
        int: 업데이트된 Sequence 수
    """
    try:
        # 모든 활성화된 Sequence 조회
        sequences = db.query(ProcedureSequence).filter(ProcedureSequence.Release == 1).all()
        
        # GroupID별로 그룹화
        sequence_groups = {}
        for sequence in sequences:
            if sequence.GroupID not in sequence_groups:
                sequence_groups[sequence.GroupID] = []
            sequence_groups[sequence.GroupID].append(sequence)
        
        # 각 Sequence 그룹의 Procedure_Cost 재계산
        updated_count = 0
        for group_id, group_sequences in sequence_groups.items():
            total_cost = 0
            
            for sequence in group_sequences:
                step_cost = 0
                
                # Element 기반 Step
                if sequence.Element_ID:
                    element = db.query(ProcedureElement).filter(
                        ProcedureElement.ID == sequence.Element_ID,
                        ProcedureElement.Release == 1
                    ).first()
                    if element:
                        step_cost = element.Procedure_Cost
                
                # Bundle 기반 Step
                elif sequence.Bundle_ID:
                    bundles = db.query(ProcedureBundle).filter(
                        ProcedureBundle.GroupID == sequence.Bundle_ID,
                        ProcedureBundle.Release == 1
                    ).all()
                    if bundles:
                        step_cost = sum(bundle.Element_Cost for bundle in bundles)
                
                # Custom 기반 Step
                elif sequence.Custom_ID:
                    custom = db.query(ProcedureCustom).filter(
                        ProcedureCustom.ID == sequence.Custom_ID,
                        ProcedureCustom.Release == 1
                    ).first()
                    if custom:
                        step_cost = custom.Element_Cost
                
                total_cost += step_cost
            
            # 그룹의 모든 Sequence에 동일한 Procedure_Cost 설정
            for sequence in group_sequences:
                sequence.Procedure_Cost = total_cost
                updated_count += 1
        
        db.commit()
        return updated_count
    except Exception as e:
        db.rollback()
        print(f"Sequence Procedure_Cost 벌크 업데이트 중 오류: {str(e)}")
        raise

def get_product_procedure_cost(product, db: Session) -> int:
    """
    Product의 Procedure_Cost 조회 (헬퍼 함수)
    """
    try:
        procedure_cost = 0
        
        if product.Element_ID:
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == product.Element_ID,
                ProcedureElement.Release == 1
            ).first()
            if element:
                procedure_cost = element.Procedure_Cost
        
        elif product.Bundle_ID:
            bundles = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == product.Bundle_ID,
                ProcedureBundle.Release == 1
            ).all()
            if bundles:
                procedure_cost = sum(bundle.Element_Cost for bundle in bundles)
        
        elif product.Custom_ID:
            customs = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == product.Custom_ID,
                ProcedureCustom.Release == 1
            ).all()
            if customs:
                procedure_cost = sum(custom.Element_Cost for custom in customs)
        
        elif product.Sequence_ID:
            # Sequence의 경우 GroupID로 조회하여 모든 Step의 비용을 합산
            sequences = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID == product.Sequence_ID,
                ProcedureSequence.Release == 1
            ).all()
            if sequences:
                procedure_cost = sum(seq.Procedure_Cost for seq in sequences)
        
        return procedure_cost
    except Exception as e:
        print(f"Product Procedure_Cost 계산 중 오류: {str(e)}")
        return 0

def update_product_margin(product, procedure_cost: int) -> bool:
    """
    Product의 마진 업데이트 (헬퍼 함수)
    """
    try:
        if product.Sell_Price is not None and procedure_cost is not None:
            product.Procedure_Cost = procedure_cost
            product.Margin = product.Sell_Price - procedure_cost
            if product.Sell_Price > 0:
                product.Margin_Rate = product.Margin / product.Sell_Price
            return True
        return False
    except Exception as e:
        print(f"Product 마진 업데이트 중 오류: {str(e)}")
        return False

def bulk_update_product_margins(db: Session) -> int:
    """
    모든 Product의 마진을 벌크 업데이트 (통일된 함수)
    
    Returns:
        int: 업데이트된 Product 수
    """
    try:
        updated_count = 0
        
        # Product_Event 마진 재계산
        event_products = db.query(ProductEvent).filter(ProductEvent.Release == 1).all()
        for product in event_products:
            procedure_cost = get_product_procedure_cost(product, db)
            if update_product_margin(product, procedure_cost):
                updated_count += 1
        
        # Product_Standard 마진 재계산
        standard_products = db.query(ProductStandard).filter(ProductStandard.Release == 1).all()
        for product in standard_products:
            procedure_cost = get_product_procedure_cost(product, db)
            if update_product_margin(product, procedure_cost):
                updated_count += 1
        
        db.commit() 
        return updated_count
    except Exception as e:
        db.rollback()
        print(f"Product 마진 벌크 업데이트 중 오류: {str(e)}")
        raise

# ============================================================================
# Consumable 변경 시 연쇄 업데이트 함수: 소모품이랑 의사 인건비는 같이 수정될 이유가 없음.
# ============================================================================

"""
    특정 Consumable을 사용하는 모든 Element의 Procedure_Cost를 벌크 업데이트
    
    Returns:
        int: 업데이트된 Element 수
"""
def bulk_update_elements_by_consumable(db: Session, consumable_id: int, global_settings: Global) -> int:
    try:
        # 해당 Consumable을 사용하는 모든 활성화된 Element 조회
        elements = db.query(ProcedureElement).filter(
            ProcedureElement.Consum_1_ID == consumable_id,
            ProcedureElement.Release == 1
        ).all()
        
        # Consumable 정보 조회
        consumable = db.query(Consumables).filter(
            Consumables.ID == consumable_id,
            Consumables.Release == 1
        ).first()
        
        # 각 Element의 Procedure_Cost 재계산 (통일된 함수 사용)
        for element in elements:
            new_cost = calculate_element_procedure_cost_from_element(element, global_settings, consumable)
            element.Procedure_Cost = new_cost
        
        db.commit()
        return len(elements)
    except Exception as e:
        db.rollback()
        print(f"Consumable 기반 Element Procedure_Cost 벌크 업데이트 중 오류: {str(e)}")
        raise

"""
    Consumable 변경 시 관련 테이블들만 연쇄 업데이트
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
"""
def cascade_update_by_consumable(db: Session, consumable_id: int, global_settings: Global) -> Dict[str, int]:
    try:
        results = {}
        
        # 1. 해당 Consumable을 사용하는 Element들의 Procedure_Cost 재계산
        results['elements'] = bulk_update_elements_by_consumable(db, consumable_id, global_settings)
        
        # 2. 모든 Bundle Element_Cost 재계산 (Element 변경으로 인해)
        results['bundles'] = bulk_update_bundle_element_costs(db)
        
        # 3. 모든 Custom Element_Cost 재계산 (Element 변경으로 인해)
        results['customs'] = bulk_update_custom_element_costs(db)
        
        # 4. 모든 Sequence Procedure_Cost 재계산 (Element 변경으로 인해)
        results['sequences'] = bulk_update_sequence_procedure_costs(db)
        
        # 5. 모든 Product 마진 재계산 (Element 변경으로 인해)
        results['products'] = bulk_update_product_margins(db)
        
        return results
    except Exception as e:
        print(f"Consumable 기반 연쇄 업데이트 중 오류: {str(e)}")
        raise

# ============================================================================
# 전체 시스템 연쇄 업데이트 함수
# ============================================================================

def cascade_update_all_tables(db: Session, global_settings: Global) -> Dict[str, int]:
    """
    Global 설정 변경 시 전체 시스템 연쇄 업데이트
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    try:
        results = {}
        
        # 1. 모든 Element Procedure_Cost 재계산
        results['elements'] = bulk_update_element_procedure_costs(db, global_settings)
        
        # 2. 모든 Bundle Element_Cost 재계산
        results['bundles'] = bulk_update_bundle_element_costs(db)
        
        # 3. 모든 Custom Element_Cost 재계산
        results['customs'] = bulk_update_custom_element_costs(db)
        
        # 4. 모든 Sequence Procedure_Cost 재계산
        results['sequences'] = bulk_update_sequence_procedure_costs(db)
        
        # 5. 모든 Product 마진 재계산
        results['products'] = bulk_update_product_margins(db)
        
        return results
    except Exception as e:
        print(f"전체 시스템 연쇄 업데이트 중 오류: {str(e)}")
        raise

# ============================================================================
# Element 변경 시 연쇄 업데이트 함수
# ============================================================================

def cascade_update_by_element_obj(element: ProcedureElement, db: Session) -> Dict[str, int]:
    """
    Element 객체로 상위 테이블 연쇄 업데이트 (Element API용)
    
    Args:
        element: Element 객체
        db: 데이터베이스 세션
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    try:
        results = {}
        
        if not element:
            print("Element 객체가 없습니다.")
            return {'bundles': 0, 'customs': 0, 'sequences': 0, 'products': 0}
        
        # 1. 해당 Element를 참조하는 Bundle들의 Element_Cost 재계산
        bundles = db.query(ProcedureBundle).filter(
            ProcedureBundle.Element_ID == element.ID,
            ProcedureBundle.Release == 1
        ).all()
        
        for bundle in bundles:
            bundle.Element_Cost = element.Procedure_Cost
        
        results['bundles'] = len(bundles)
        
        # 2. 해당 Element를 참조하는 Custom들의 Element_Cost 재계산 (Custom Count 적용)
        customs = db.query(ProcedureCustom).filter(
            ProcedureCustom.Element_ID == element.ID,
            ProcedureCustom.Release == 1
        ).all()
        
        for custom in customs:
            # Custom Count를 적용한 비용 계산
            custom.Element_Cost = element.Procedure_Cost * custom.Custom_Count
        
        results['customs'] = len(customs)
        
        # 3. 해당 Element를 포함하는 Sequence들의 Procedure_Cost 재계산
        results['sequences'] = update_sequences_by_element(element.ID, db)
        
        # 4. 해당 Element를 포함하는 Product들의 마진 재계산
        results['products'] = update_products_by_element(element.ID, db)
        
        return results
    except Exception as e:
        print(f"Element 기반 연쇄 업데이트 중 오류: {str(e)}")
        raise

def update_sequences_by_element(element_id: int, db: Session) -> int:
    """
    특정 Element가 포함된 Sequence들의 Procedure_Cost 재계산
    
    Args:
        element_id: Element ID
        db: 데이터베이스 세션
    
    Returns:
        int: 업데이트된 Sequence 수
    """
    try:
        # 해당 Element를 직접 참조하는 Sequence들
        direct_sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.Element_ID == element_id,
            ProcedureSequence.Release == 1
        ).all()
        
        # 해당 Element가 포함된 Bundle을 참조하는 Sequence들
        bundle_sequences = db.query(ProcedureSequence).join(
            ProcedureBundle, 
            ProcedureSequence.Bundle_ID == ProcedureBundle.GroupID
        ).filter(
            ProcedureBundle.Element_ID == element_id,
            ProcedureSequence.Release == 1
        ).all()
        
        # 해당 Element가 포함된 Custom을 참조하는 Sequence들
        custom_sequences = db.query(ProcedureSequence).join(
            ProcedureCustom,
            ProcedureSequence.Custom_ID == ProcedureCustom.ID
        ).filter(
            ProcedureCustom.Element_ID == element_id,
            ProcedureSequence.Release == 1
        ).all()
        
        # 모든 관련 Sequence 수집
        all_sequences = list(set(direct_sequences + bundle_sequences + custom_sequences))
        
        # GroupID별로 그룹화하여 Procedure_Cost 재계산
        sequence_groups = {}
        for sequence in all_sequences:
            if sequence.GroupID not in sequence_groups:
                sequence_groups[sequence.GroupID] = []
            sequence_groups[sequence.GroupID].append(sequence)
        
        updated_count = 0
        for group_id, group_sequences in sequence_groups.items():
            total_cost = 0
            
            for sequence in group_sequences:
                step_cost = 0
                
                # Element 기반 Step
                if sequence.Element_ID:
                    element = db.query(ProcedureElement).filter(
                        ProcedureElement.ID == sequence.Element_ID,
                        ProcedureElement.Release == 1
                    ).first()
                    if element:
                        step_cost = element.Procedure_Cost
                
                # Bundle 기반 Step
                elif sequence.Bundle_ID:
                    bundles = db.query(ProcedureBundle).filter(
                        ProcedureBundle.GroupID == sequence.Bundle_ID,
                        ProcedureBundle.Release == 1
                    ).all()
                    if bundles:
                        step_cost = sum(bundle.Element_Cost for bundle in bundles)
                
                # Custom 기반 Step
                elif sequence.Custom_ID:
                    custom = db.query(ProcedureCustom).filter(
                        ProcedureCustom.ID == sequence.Custom_ID,
                        ProcedureCustom.Release == 1
                    ).first()
                    if custom:
                        step_cost = custom.Element_Cost
                
                total_cost += step_cost
            
            # 그룹의 모든 Sequence에 동일한 Procedure_Cost 설정
            for sequence in group_sequences:
                sequence.Procedure_Cost = total_cost
                updated_count += 1
        
        return updated_count
    except Exception as e:
        print(f"Element 기반 Sequence 업데이트 중 오류: {str(e)}")
        raise

def update_products_by_element(element_id: int, db: Session) -> int:
    """
    특정 Element가 포함된 Product들의 마진 재계산
    
    Args:
        element_id: Element ID
        db: 데이터베이스 세션
    
    Returns:
        int: 업데이트된 Product 수
    """
    try:
        updated_count = 0
        
        # 해당 Element를 직접 참조하는 Product들
        direct_products = db.query(ProductStandard).filter(
            ProductStandard.Element_ID == element_id,
            ProductStandard.Release == 1
        ).all()
        
        direct_event_products = db.query(ProductEvent).filter(
            ProductEvent.Element_ID == element_id,
            ProductEvent.Release == 1
        ).all()
        
        # 해당 Element가 포함된 Bundle을 참조하는 Product들
        bundle_products = db.query(ProductStandard).join(
            ProcedureBundle,
            ProductStandard.Bundle_ID == ProcedureBundle.GroupID
        ).filter(
            ProcedureBundle.Element_ID == element_id,
            ProductStandard.Release == 1
        ).all()
        
        bundle_event_products = db.query(ProductEvent).join(
            ProcedureBundle,
            ProductEvent.Bundle_ID == ProcedureBundle.GroupID
        ).filter(
            ProcedureBundle.Element_ID == element_id,
            ProductEvent.Release == 1
        ).all()
        
        # 해당 Element가 포함된 Custom을 참조하는 Product들
        custom_products = db.query(ProductStandard).join(
            ProcedureCustom,
            ProductStandard.Custom_ID == ProcedureCustom.GroupID
        ).filter(
            ProcedureCustom.Element_ID == element_id,
            ProductStandard.Release == 1
        ).all()
        
        custom_event_products = db.query(ProductEvent).join(
            ProcedureCustom,
            ProductEvent.Custom_ID == ProcedureCustom.GroupID
        ).filter(
            ProcedureCustom.Element_ID == element_id,
            ProductEvent.Release == 1
        ).all()
        
        # 해당 Element가 포함된 Sequence를 참조하는 Product들
        sequence_products = db.query(ProductStandard).join(
            ProcedureSequence,
            ProductStandard.Sequence_ID == ProcedureSequence.ID
        ).filter(
            ProcedureSequence.Element_ID == element_id,
            ProductStandard.Release == 1
        ).all()
        
        sequence_event_products = db.query(ProductEvent).join(
            ProcedureSequence,
            ProductEvent.Sequence_ID == ProcedureSequence.ID
        ).filter(
            ProcedureSequence.Element_ID == element_id,
            ProductEvent.Release == 1
        ).all()
        
        # 모든 관련 Product 수집
        all_products = (
            direct_products + direct_event_products +
            bundle_products + bundle_event_products +
            custom_products + custom_event_products +
            sequence_products + sequence_event_products
        )
        
        # 중복 제거
        unique_products = list(set(all_products))
        
        # 각 Product의 마진 재계산
        for product in unique_products:
            procedure_cost = get_product_procedure_cost(product, db)
            if update_product_margin(product, procedure_cost):
                updated_count += 1
        
        return updated_count
    except Exception as e:
        print(f"Element 기반 Product 업데이트 중 오류: {str(e)}")
        raise



# 기존 함수명 호환성을 위해 유지 (함수 정의 순서 조정)
def cascade_update_by_element(element_id: int, db: Session, element_obj: ProcedureElement = None) -> Dict[str, int]:
    """
    Element 변경 시 상위 테이블 연쇄 업데이트 (호환성 유지)
    
    Args:
        element_id: Element ID
        db: 데이터베이스 세션
        element_obj: Element 객체 (선택적)
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    if element_obj is not None:
        return cascade_update_by_element_obj(element_obj, db)
    else:
        # Element ID로 조회 후 객체 함수 호출
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id
        ).first()
        
        if not element:
            print(f"Element {element_id}를 찾을 수 없습니다.")
            return {'bundles': 0, 'customs': 0, 'sequences': 0, 'products': 0}
        
        return cascade_update_by_element_obj(element, db)

def cascade_update_by_bundle_group(bundle_group_id: int, db: Session) -> Dict[str, int]:
    """
    Bundle 그룹 변경 시 상위 테이블 연쇄 업데이트
    
    Args:
        bundle_group_id: Bundle GroupID
        db: 데이터베이스 세션
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    try:
        results = {}
        
        # 1. 해당 Bundle 그룹을 참조하는 Sequence들의 Procedure_Cost 재계산
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.Bundle_ID == bundle_group_id,
            ProcedureSequence.Release == 1
        ).all()
        
        for sequence in sequences:
            # Sequence의 Procedure_Cost 재계산
            sequence.Procedure_Cost = get_sequence_procedure_cost(sequence, db)
        
        results['sequences'] = len(sequences)
        
        # 2. 해당 Sequence들을 참조하는 Product들의 마진 재계산
        sequence_ids = [seq.ID for seq in sequences]
        products = db.query(ProductStandard).filter(
            ProductStandard.Sequence_ID.in_(sequence_ids),
            ProductStandard.Release == 1
        ).all()
        
        for product in products:
            procedure_cost = get_product_procedure_cost(product, db)
            update_product_margin(product, procedure_cost)
        
        results['products_standard'] = len(products)
        
        # 3. Event Product들도 재계산
        event_products = db.query(ProductEvent).filter(
            ProductEvent.Sequence_ID.in_(sequence_ids),
            ProductEvent.Release == 1
        ).all()
        
        for product in event_products:
            procedure_cost = get_product_procedure_cost(product, db)
            update_product_margin(product, procedure_cost)
        
        results['products_event'] = len(event_products)
        
        # 변경사항 커밋
        db.commit()
        
        return results
    except Exception as e:
        print(f"Bundle 그룹 기반 연쇄 업데이트 중 오류: {str(e)}")
        raise

def cascade_update_by_custom_group(custom_group_id: int, db: Session) -> Dict[str, int]:
    """
    Custom 그룹 변경 시 상위 테이블 연쇄 업데이트
    
    Args:
        custom_group_id: Custom GroupID
        db: 데이터베이스 세션
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    try:
        results = {}
        
        # 1. 해당 Custom 그룹을 참조하는 Sequence들의 Procedure_Cost 재계산
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.Custom_ID == custom_group_id,
            ProcedureSequence.Release == 1
        ).all()
        
        for sequence in sequences:
            # Sequence의 Procedure_Cost 재계산
            sequence.Procedure_Cost = get_sequence_procedure_cost(sequence, db)
        
        results['sequences'] = len(sequences)
        
        # 2. 해당 Sequence들을 참조하는 Product들의 마진 재계산
        sequence_ids = [seq.ID for seq in sequences]
        products = db.query(ProductStandard).filter(
            ProductStandard.Sequence_ID.in_(sequence_ids),
            ProductStandard.Release == 1
        ).all()
        
        for product in products:
            procedure_cost = get_product_procedure_cost(product, db)
            update_product_margin(product, procedure_cost)
        
        results['products_standard'] = len(products)
        
        # 3. Event Product들도 재계산
        event_products = db.query(ProductEvent).filter(
            ProductEvent.Sequence_ID.in_(sequence_ids),
            ProductEvent.Release == 1
        ).all()
        
        for product in event_products:
            procedure_cost = get_product_procedure_cost(product, db)
            update_product_margin(product, procedure_cost)
        
        results['products_event'] = len(event_products)
        
        # 변경사항 커밋
        db.commit()
        
        return results
    except Exception as e:
        print(f"Custom 그룹 연쇄 업데이트 중 오류: {str(e)}")
        db.rollback()
        raise

def cascade_update_by_sequence_group(sequence_group_id: int, db: Session) -> Dict[str, int]:
    """
    Sequence 그룹 변경 시 상위 테이블 연쇄 업데이트
    
    Args:
        sequence_group_id: Sequence GroupID
        db: 데이터베이스 세션
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    try:
        results = {}
        
        # 1. 해당 Sequence 그룹을 참조하는 Product들의 마진 재계산
        try:
            products = db.query(ProductStandard).filter(
                ProductStandard.Sequence_ID == sequence_group_id,
                ProductStandard.Release == 1
            ).all()
            
            for product in products:
                try:
                    procedure_cost = get_product_procedure_cost(product, db)
                    update_product_margin(product, procedure_cost)
                except Exception as product_error:
                    print(f"Product {product.ID} 마진 업데이트 중 오류: {str(product_error)}")
                    continue
            
            results['products_standard'] = len(products)
        except Exception as standard_error:
            print(f"ProductStandard 조회 중 오류: {str(standard_error)}")
            results['products_standard'] = 0
        
        # 2. Event Product들도 재계산
        try:
            event_products = db.query(ProductEvent).filter(
                ProductEvent.Sequence_ID == sequence_group_id,
                ProductEvent.Release == 1
            ).all()
            
            for product in event_products:
                try:
                    procedure_cost = get_product_procedure_cost(product, db)
                    update_product_margin(product, procedure_cost)
                except Exception as product_error:
                    print(f"ProductEvent {product.ID} 마진 업데이트 중 오류: {str(product_error)}")
                    continue
            
            results['products_event'] = len(event_products)
        except Exception as event_error:
            print(f"ProductEvent 조회 중 오류: {str(event_error)}")
            results['products_event'] = 0
        
        # 변경사항 커밋
        try:
            db.commit()
        except Exception as commit_error:
            print(f"연쇄 업데이트 커밋 중 오류: {str(commit_error)}")
            db.rollback()
        
        return results
    except Exception as e:
        print(f"Sequence 그룹 연쇄 업데이트 중 오류: {str(e)}")
        try:
            db.rollback()
        except:
            pass
        # 예외를 다시 발생시키지 않고 결과만 반환
        return {'products_standard': 0, 'products_event': 0}

def get_sequence_procedure_cost(sequence: ProcedureSequence, db: Session) -> int:
    """
    Sequence의 Procedure_Cost 계산
    
    Args:
        sequence: Sequence 객체
        db: 데이터베이스 세션
    
    Returns:
        int: 계산된 Procedure_Cost
    """
    try:
        if sequence.Element_ID:
            # Element 기반 계산
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == sequence.Element_ID,
                ProcedureElement.Release == 1
            ).first()
            return element.Procedure_Cost if element else 0
        elif sequence.Bundle_ID:
            # Bundle 기반 계산
            bundles = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == sequence.Bundle_ID,
                ProcedureBundle.Release == 1
            ).all()
            total_cost = sum(bundle.Element_Cost for bundle in bundles)
            print(f"Bundle {sequence.Bundle_ID}의 총 비용: {total_cost}")
            return total_cost
        elif sequence.Custom_ID:
            # Custom 기반 계산
            custom = db.query(ProcedureCustom).filter(
                ProcedureCustom.ID == sequence.Custom_ID,
                ProcedureCustom.Release == 1
            ).first()
            return custom.Element_Cost if custom else 0
        else:
            return 0
    except Exception as e:
        print(f"Sequence Procedure_Cost 계산 중 오류: {str(e)}")
        return 0



def update_element_references(old_element_id: int, new_element_id: int, db: Session) -> Dict[str, int]:
    """
    Element ID 변경 시 상위 테이블들의 Element_ID 참조 업데이트
    
    Args:
        old_element_id: 변경 전 Element ID
        new_element_id: 변경 후 Element ID
        db: 데이터베이스 세션
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    try:
        results = {}
        
        # 1. Bundle 테이블의 Element_ID 업데이트
        bundles = db.query(ProcedureBundle).filter(
            ProcedureBundle.Element_ID == old_element_id,
            ProcedureBundle.Release == 1
        ).all()
        
        for bundle in bundles:
            bundle.Element_ID = new_element_id
        
        results['bundles'] = len(bundles)
        
        # 2. Custom 테이블의 Element_ID 업데이트
        customs = db.query(ProcedureCustom).filter(
            ProcedureCustom.Element_ID == old_element_id,
            ProcedureCustom.Release == 1
        ).all()
        
        for custom in customs:
            custom.Element_ID = new_element_id
        
        results['customs'] = len(customs)
        
        # 3. Sequence 테이블의 Element_ID 업데이트
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.Element_ID == old_element_id,
            ProcedureSequence.Release == 1
        ).all()
        
        for sequence in sequences:
            sequence.Element_ID = new_element_id
        
        results['sequences'] = len(sequences)
        
        # 4. Product_Standard 테이블의 Element_ID 업데이트
        product_standards = db.query(ProductStandard).filter(
            ProductStandard.Element_ID == old_element_id,
            ProductStandard.Release == 1
        ).all()
        
        for product in product_standards:
            product.Element_ID = new_element_id
        
        results['product_standards'] = len(product_standards)
        
        # 5. Product_Event 테이블의 Element_ID 업데이트
        product_events = db.query(ProductEvent).filter(
            ProductEvent.Element_ID == old_element_id,
            ProductEvent.Release == 1
        ).all()
        
        for product in product_events:
            product.Element_ID = new_element_id
        
        results['product_events'] = len(product_events)
        
        return results
    except Exception as e:
        print(f"Element 참조 업데이트 중 오류: {str(e)}")
        raise

def cascade_update_bundle_group_id(old_group_id: int, new_group_id: int, db: Session) -> Dict[str, int]:
    """
    Bundle Group ID 변경 시 참조 테이블들의 Group ID를 함께 업데이트
    
    Args:
        old_group_id: 기존 Bundle GroupID
        new_group_id: 새로운 Bundle GroupID
        db: 데이터베이스 세션
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    try:
        results = {}
        
        # 1. Sequence 테이블에서 Bundle_ID 업데이트
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.Bundle_ID == old_group_id,
            ProcedureSequence.Release == 1
        ).all()
        
        for sequence in sequences:
            sequence.Bundle_ID = new_group_id
        
        results['sequences'] = len(sequences)
        
        # 2. ProductStandard 테이블에서 Bundle_ID 업데이트
        products_standard = db.query(ProductStandard).filter(
            ProductStandard.Bundle_ID == old_group_id,
            ProductStandard.Release == 1
        ).all()
        
        for product in products_standard:
            product.Bundle_ID = new_group_id
        
        results['products_standard'] = len(products_standard)
        
        # 3. ProductEvent 테이블에서 Bundle_ID 업데이트
        products_event = db.query(ProductEvent).filter(
            ProductEvent.Bundle_ID == old_group_id,
            ProductEvent.Release == 1
        ).all()
        
        for product in products_event:
            product.Bundle_ID = new_group_id
        
        results['products_event'] = len(products_event)
        
        # 변경사항 커밋
        db.commit()
        
        return results
    except Exception as e:
        print(f"Bundle Group ID 변경 연쇄 업데이트 중 오류: {str(e)}")
        raise

def cascade_update_custom_group_id(old_group_id: int, new_group_id: int, db: Session) -> Dict[str, int]:
    """
    Custom Group ID 변경 시 참조 테이블들의 Group ID를 함께 업데이트
    
    Args:
        old_group_id: 기존 Custom GroupID
        new_group_id: 새로운 Custom GroupID
        db: 데이터베이스 세션
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    try:
        results = {}
        
        # 1. Sequence 테이블에서 Custom_ID 업데이트
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.Custom_ID == old_group_id,
            ProcedureSequence.Release == 1
        ).all()
        
        for sequence in sequences:
            sequence.Custom_ID = new_group_id
        
        results['sequences'] = len(sequences)
        
        # 2. ProductStandard 테이블에서 Custom_ID 업데이트
        products_standard = db.query(ProductStandard).filter(
            ProductStandard.Custom_ID == old_group_id,
            ProductStandard.Release == 1
        ).all()
        
        for product in products_standard:
            product.Custom_ID = new_group_id
        
        results['products_standard'] = len(products_standard)
        
        # 3. ProductEvent 테이블에서 Custom_ID 업데이트
        products_event = db.query(ProductEvent).filter(
            ProductEvent.Custom_ID == old_group_id,
            ProductEvent.Release == 1
        ).all()
        
        for product in products_event:
            product.Custom_ID = new_group_id
        
        results['products_event'] = len(products_event)
        
        # 변경사항 커밋
        db.commit()
        
        return results
    except Exception as e:
        print(f"Custom Group ID 변경 연쇄 업데이트 중 오류: {str(e)}")
        raise

def cascade_update_membership_id(old_membership_id: int, new_membership_id: int, db: Session) -> Dict[str, int]:
    """
    Membership ID 변경 시 참조 테이블들의 Membership ID를 함께 업데이트
    
    Args:
        old_membership_id: 기존 Membership ID
        new_membership_id: 새로운 Membership ID
        db: 데이터베이스 세션
    
    Returns:
        Dict[str, int]: 각 테이블별 업데이트된 레코드 수
    """
    try:
        results = {}
        
        # 1. Info_Membership 테이블에서 Membership_ID 업데이트
        info_memberships = db.query(InfoMembership).filter(
            InfoMembership.Membership_ID == old_membership_id,
            InfoMembership.Release == 1
        ).all()
        
        for info in info_memberships:
            info.Membership_ID = new_membership_id
        
        results['info_memberships'] = len(info_memberships)
        
        # 변경사항 커밋
        db.commit()
        
        return results
    except Exception as e:
        print(f"Membership ID 변경 연쇄 업데이트 중 오류: {str(e)}")
        raise
