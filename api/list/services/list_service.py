"""
    [ Read API 목록 조회 서비스 - 최적화 버전 ]
    N+1 쿼리 문제를 해결한 최적화된 상품 목록 조회 비즈니스 로직
"""

from sqlalchemy.orm import Session
from typing import Any, Dict, List
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence

""" 시술 정보를 조회하고 Dict로 반환하는 공통 함수 """
def process_procedure_data(
    db: Session, 
    products: List[Any], 
    element_ids: List[int], 
    bundle_ids: List[int], 
    custom_ids: List[int], 
    sequence_ids: List[int]
) -> Dict[int, Dict[str, List]]:
    """
    ORM 객체 리스트에서 Procedure 정보를 조회하여 Dict로 반환
    
    Returns:
        {
            product_id: {
                "procedure_names": [...],
                "class_types": [...]
            }
        }
    """
    
    # 결과를 담을 딕셔너리 초기화
    result = {product.ID: {"procedure_names": [], "class_types": []} for product in products}
    
    # 1. Element 시술 정보 일괄 조회: element Name, Class_Type 추가 완
    if element_ids:
        elements = db.query(ProcedureElement).filter(ProcedureElement.ID.in_(element_ids)).all()
        element_dict = {
            e.ID: e for e in elements
        }
        # element_dict: {
        #   1: <ProcedureElement(ID=1, Name='시술1')>, 
        #   2: <ProcedureElement(ID=2, Name='시술2')>
        # }
        
        # 상품의 ID와 Element_ID가 같은 경우 시술 정보를 조회하기 위한 for문
        for product in products:
            # product의 Element_ID와 element_dict의 ID가 같을 경우,
            if product.Element_ID and product.Element_ID in element_dict:
                # product의 Element_ID를 element_dict의 ID와 매칭시켜 해당 데이터를 element에 담기: element = element_dict[10] >> <ProcedureElement(ID=10, Name='시술1')>
                element = element_dict[product.Element_ID]

                # result의 key = product_id의 value에 있는 procedure_names 리스트에 element.Name을 추가
                result[product.ID]["procedure_names"].append(element.Name)
                # result의 key = product_id의 value에 있는 class_types 리스트에 element.Class_Type을 추가 (Optional)
                if element.Class_Type:
                    result[product.ID]["class_types"].append(element.Class_Type)

            # element_ids 조회 완료 result: {1: {'procedure_names': ['시술'], 'class_types': []}}
    

    # 2. Bundle 시술 정보 일괄 조회: element Name, Class_Type 추가 완
    if bundle_ids:
        # ProcedureElement랑 ProcedureBundle 테이블을 조인하여 bundle_ids에 있는 GroupID와 같은 데이터를 조회 (Bundle의 Element_ID와 Elmenet의 ID가 같은 경우)
        bundle_elements = db.query(
            ProcedureElement,
            ProcedureBundle.GroupID
        ).join(
            ProcedureBundle, ProcedureElement.ID == ProcedureBundle.Element_ID
        ).filter(ProcedureBundle.GroupID.in_(bundle_ids)).all()

        # [ 쿼리 결과 ]
        #     bundle_elements = [
        #       (<ProcedureElement(ID=11000)>, 10020),  => 시술 11000이 Bundle GroupID 10020에 속함
        #       (<ProcedureElement(ID=11000)>, 10060),  => 시술 11000이 Bundle GroupID 10060에도 속함
        #       (<ProcedureElement(ID=11010)>, 10140),  => 시술 11010이 Bundle GroupID 10140에 속함
        #     ]
                            
        # bundle_elements: (<ProcedureElement(ID = int, Name = 'string')>, GroupID:int)

        # Bundle ID별로 그룹화: key: GroupID, value: ProcedureElement Object List
        bundle_dict = {}
        # bundle_dict = {
        #    1: [
        #        <ProcedureElement(ID=1, Name='시술1')>, 
        #        <ProcedureElement(ID=2, Name='시술2')>
        #    ], 
        #    
        #    2: [
        #        <ProcedureElement(ID=3, Name='시술3')>
        #    ]
        # }

        
        # bundle_elements 안에 모든 element를 순회하면서 bundle_dict에 추가
        for element, group_id in bundle_elements:
            # bundle_dict에 element_group.GroupID가 없는 경우, 빈 리스트 반환
            if group_id not in bundle_dict:
                bundle_dict[group_id] = []

            # element_group.GroupID를 key로 하는 리스트에 element_group을 추가: GroupID를 기준으로 그룹화
            bundle_dict[group_id].append(element)
            
            # [ 그룹화 결과 ]
            #   bundle_dict = {
            #      10020: [
            #          (<ProcedureElement(ID=11000)>, 10020),
            #          (<ProcedureElement(ID=11040)>, 10020)
            #      ],
            #      
            #       10060: [
            #          (<ProcedureElement(ID=11000)>, 10060)
            #      ]
            #    }

        
        # 상품의 ID와 Bundle_ID가 같은 경우 시술 정보를 조회하기 위한 for문
        for product in products:
            # 상품의 Bundle_ID와 bundle_dict의 key(GroupID)가 같은 경우, 시술 정보를 조회하기 위한 if문
            if product.Bundle_ID and product.Bundle_ID in bundle_dict:
                # bundle_dict[product.Bundle_ID]의 모든 element와 _group_id를 순회하면서 result에 추가 (group_id는 tuple 언패킹을 위한 _변수)
                for element in bundle_dict[product.Bundle_ID]:
                    # result의 key = product_id의 value에 있는 procedure_names 리스트에 element.Name을 추가
                    result[product.ID]["procedure_names"].append(element.Name)
                    
                    # result의 key = product_id의 value에 있는 class_types 리스트에 element.Class_Type을 추가 (Optional)
                    if element.Class_Type and element.Class_Type not in result[product.ID]["class_types"]:
                        result[product.ID]["class_types"].append(element.Class_Type)
            
            # bundle_ids 조회 완료 result: {1: {'procedure_names': ['시술1', '시술2'], 'class_types': []}}
    

    # 3. Custom 시술 정보 일괄 조회: element Name, Class_Type 추가 완
    if custom_ids:
        # ProcedureElement와 ProcedureCustom 테이블을 조인하여 custom_ids에 있는 GroupID와 같은 데이터를 조회 (Custom의 Element_ID와 Elmenet의 ID가 같은 경우)
        custom_elements = db.query(
            ProcedureElement,
            ProcedureCustom.GroupID
        ).join(
            ProcedureCustom, ProcedureElement.ID == ProcedureCustom.Element_ID
        ).filter(ProcedureCustom.GroupID.in_(custom_ids)).all()

        # [ 쿼리 결과 ]
        #   custom_elements = [
        #       (<ProcedureElement(ID=74140, Name='재생관리 1회')>, 10010),
        #       (<ProcedureElement(ID=74140, Name='재생관리 1회')>, 10020),
        #       (<ProcedureElement(ID=74140, Name='재생관리 1회')>, 10030),
        #       (<ProcedureElement(ID=74170, Name='오멜론 LED')>, 10030),
        #       (<ProcedureElement(ID=74180, Name='클랜징')>, 10030),
        #       (<ProcedureElement(ID=90000, Name='모델링팩')>, 10030),
        #       (<ProcedureElement(ID=90000, Name='모델링팩')>, 10030)
        #   ]
        
        # custom_elements 안에 모든 element를 순회하면서 추가할 딕셔너리 생성
        custom_dict = {}
        
        # custom_dict: key: GroupID, value: ProcedureElement Object List
        for element, group_id in custom_elements:
            
            # custom_dict에 custom_id가 없는 경우, 빈 리스트 반환
            if group_id not in custom_dict:
                custom_dict[group_id] = []
            
            # custom_dict에 group_id를 key로 하는 리스트에 element를 추가
            custom_dict[group_id].append(element)

            # [ 그룹화 결과 ]
            #   custom_dict = {
            #      20040: [
            #          <ProcedureElement(ID=20000, Name='포텐자 모공')>,
            #          <ProcedureElement(ID=20090, Name='디오레 피부재생 1회')>,
            #          <ProcedureElement(ID=20190, Name='피코슈어 부분토닝 1회')>,
            #          <ProcedureElement(ID=20340, Name='엑셀V플러스 홍조 1회')>,
            #      ],
            #      
            #      20050: [
            #          <ProcedureElement(ID=20000, Name='아쿠아포텐자')>,
            #          <ProcedureElement(ID=20090, Name='아쿠아디오레 피부재생 1회')>,
            #          <ProcedureElement(ID=20190, Name='아쿠아슈어 부분토닝 1회')>,
            #          <ProcedureElement(ID=20340, Name='아쿠아V플러스 홍조 1회')>,
            #      ]
            #   }
        
        # 상품의 Custom_ID와 custom_dict의 key(GroupID)가 같은 경우 시술 정보를 조회하기 위한 for문
        for product in products:
            
            # custom_dict에 product.Custom_ID가 있는 경우 시술 정보를 조회하기 위한 if문
            if product.Custom_ID and product.Custom_ID in custom_dict:
                
                # custom_dict[product.Custom_ID]의 모든 element를 순회하면서 result에 추가 (group_id는 tuple 언패킹을 위한 _변수)
                for element in custom_dict[product.Custom_ID]:
                    result[product.ID]["procedure_names"].append(element.Name)
                    
                    # result의 key = product_id의 value에 있는 class_types 리스트에 element.Class_Type을 추가 (Optional)
                    if element.Class_Type and element.Class_Type not in result[product.ID]["class_types"]:
                        result[product.ID]["class_types"].append(element.Class_Type)

        
        # custom_ids 조회 완료 result: {1: {'procedure_names': ['시술1', '시술2'], 'class_types': []}}
    

    # 4. Sequence 시술 정보 배치 조회 (N+1 문제 해결)
    if sequence_ids:
        try:
            # 4-1. Sequence 기본 정보 조회
            sequence_info = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID.in_(sequence_ids)
            ).all()
            
            # 4-2. Sequence에서 참조하는 모든 ID 수집
            seq_element_ids = set()
            seq_bundle_ids = set()
            seq_custom_ids = set()
            
            for seq in sequence_info:
                if seq.Element_ID:
                    seq_element_ids.add(seq.Element_ID)
                elif seq.Bundle_ID:
                    seq_bundle_ids.add(seq.Bundle_ID)
                elif seq.Custom_ID:
                    seq_custom_ids.add(seq.Custom_ID)
            
            # 4-3. 배치 조회: Element 데이터
            seq_elements_dict = {}
            if seq_element_ids:
                seq_elements = db.query(ProcedureElement).filter(
                    ProcedureElement.ID.in_(seq_element_ids)
                ).all()
                seq_elements_dict = {e.ID: e for e in seq_elements}
            
            # 4-4. 배치 조회: Bundle 데이터
            seq_bundles_dict = {}
            seq_bundle_element_ids = set()
            if seq_bundle_ids:
                seq_bundles = db.query(ProcedureBundle).filter(
                    ProcedureBundle.GroupID.in_(seq_bundle_ids)
                ).all()
                # Bundle을 GroupID로 그룹화
                for bundle in seq_bundles:
                    if bundle.GroupID not in seq_bundles_dict:
                        seq_bundles_dict[bundle.GroupID] = []
                    seq_bundles_dict[bundle.GroupID].append(bundle)
                    if bundle.Element_ID:
                        seq_bundle_element_ids.add(bundle.Element_ID)
                
                # Bundle의 Element 정보 배치 조회
                if seq_bundle_element_ids:
                    bundle_elements = db.query(ProcedureElement).filter(
                        ProcedureElement.ID.in_(seq_bundle_element_ids)
                    ).all()
                    for element in bundle_elements:
                        seq_elements_dict[element.ID] = element
            
            # 4-5. 배치 조회: Custom 데이터
            seq_customs_dict = {}
            seq_custom_element_ids = set()
            if seq_custom_ids:
                seq_customs = db.query(ProcedureCustom).filter(
                    ProcedureCustom.GroupID.in_(seq_custom_ids)
                ).all()
                # Custom을 GroupID로 그룹화
                for custom in seq_customs:
                    if custom.GroupID not in seq_customs_dict:
                        seq_customs_dict[custom.GroupID] = []
                    seq_customs_dict[custom.GroupID].append(custom)
                    if custom.Element_ID:
                        seq_custom_element_ids.add(custom.Element_ID)
                
                # Custom의 Element 정보 배치 조회
                if seq_custom_element_ids:
                    custom_elements = db.query(ProcedureElement).filter(
                        ProcedureElement.ID.in_(seq_custom_element_ids)
                    ).all()
                    for element in custom_elements:
                        seq_elements_dict[element.ID] = element
            
            # 4-6. Sequence 데이터 구성 (메모리에서 조합)
            sequence_dict = {}
            for seq in sequence_info:
                if seq.GroupID not in sequence_dict:
                    sequence_dict[seq.GroupID] = []
                
                # Element 처리
                if seq.Element_ID and seq.Element_ID in seq_elements_dict:
                    element = seq_elements_dict[seq.Element_ID]
                    sequence_dict[seq.GroupID].append({
                        'name': element.Name,
                        'class_type': element.Class_Type
                    })
                
                # Bundle 처리
                elif seq.Bundle_ID and seq.Bundle_ID in seq_bundles_dict:
                    for bundle in seq_bundles_dict[seq.Bundle_ID]:
                        if bundle.Element_ID and bundle.Element_ID in seq_elements_dict:
                            element = seq_elements_dict[bundle.Element_ID]
                            sequence_dict[seq.GroupID].append({
                                'name': bundle.Name or element.Name,
                                'class_type': element.Class_Type
                            })
                
                # Custom 처리
                elif seq.Custom_ID and seq.Custom_ID in seq_customs_dict:
                    for custom in seq_customs_dict[seq.Custom_ID]:
                        if custom.Element_ID and custom.Element_ID in seq_elements_dict:
                            element = seq_elements_dict[custom.Element_ID]
                            sequence_dict[seq.GroupID].append({
                                'name': custom.Name or element.Name,
                                'class_type': element.Class_Type
                            })
            
            # 4-7. 결과에 Sequence 정보 추가
            for product in products:
                if product.Sequence_ID and product.Sequence_ID in sequence_dict:
                    for item in sequence_dict[product.Sequence_ID]:
                        result[product.ID]["procedure_names"].append(item['name'])
                        if item['class_type'] and item['class_type'] not in result[product.ID]["class_types"]:
                            result[product.ID]["class_types"].append(item['class_type'])
        
        except Exception as e:
            print(f"Sequence 시술 정보 조회 중 오류: {str(e)}")
            # 오류 발생 시 빈 결과로 처리
    
    # class_types 중복 제거
    for product_id in result:
        result[product_id]["class_types"] = list(set(result[product_id]["class_types"]))
    
    return result