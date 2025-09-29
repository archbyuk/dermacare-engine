"""
    [ Consumables Parser ]
        소모품 데이터를 DataFrame을 읽어 DB에 삽입하는 파서
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from ..utils.abstract_utils import AbstractUtils
from db.models.consumables import Consumables

class ConsumablesParser(AbstractUtils):
    """
        params:
            used_df: 빈 값, 사용하지 않는 컬럼, 숫자 값이 정리된 데이터프레임 (type: pd.DataFrame)
    """
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Consumables")
    
    # 필수 컬럼: ID, Name
    def validate_data(self, used_df: pd.DataFrame, filename: str) -> Tuple[bool, List[str]]:

        # 에러를 담을 리스트
        errors = []

        # 필수 컬럼 리스트
        required_columns = ['ID', 'Name', 'Release']

        # 필수 컬럼 확인: 
        #   - set은 O(1)의 시간 복잡도로 처리 가능
        #   - for문 사용 시 O(n)의 시간 복잡도로 조금 더 느림
        missing_columns = set(required_columns) - set(used_df.columns)

        # 부족한 컬럼이 있다면,
        if missing_columns:
            errors.append(
                f"{filename}의 존재하지 않는 필수 컬럼이 있습니다. \n 부족한 컬럼: {', '.join(missing_columns)}"
                # missing_columns가 set이므로, 리스트로 반환
            )
        
        # ID 컬럼 검증
        if 'ID' in used_df.columns:
            if used_df['ID'].isnull().any():
                errors.append(f"{filename}의 ID 컬럼에 NULL 값이 있습니다")
            
            if used_df['ID'].duplicated().any():
                errors.append(f"{filename}의 ID 컬럼에 중복된 값이 있습니다")

        # 숫자 컬럼 검증
        numeric_columns = ['ID', 'Release', 'I_Value', 'F_Value', 'Price', 'Unit_Price', 'VAT']
        
        # used_df와 numeric_columns의 교집합 찾기
        existing_columns = set(used_df.columns) & set(numeric_columns)

        # existing_columns에 대해, 숫자가 아닌 값이 있는지 확인
        if existing_columns:
            try:
                # 모든 숫자 컬럼을 한 번에 검증: raise 예외 발생 시 에러 리스트에 추가
                # to_numeric 함수는 숫자가 아닌 값이 있으면 ValueError 예외 발생
                # errors='coerce' 옵션을 사용하여, 숫자가 아닌 값이 있으면 NaN으로 변환
                # 이 NaN은 추후 clean_data의 normalize_data 함수에서 None으로 변환
                used_df[
                    list(existing_columns)
                ].apply(pd.to_numeric, errors='raise')
                
            except (ValueError, TypeError):
                errors.append(f"{filename}의 {existing_columns} 컬럼에 숫자가 아닌 값이 있습니다")

        return len(errors) == 0, errors


    # Consumables 테이블에 데이터 삽입 (DB insert)
    def insert_data(self, used_df: pd.DataFrame) -> Dict[str, Any]:
        
        try:
            # 트랜잭션 시작
            with self.db.begin():
                # 기존 데이터 전체 삭제
                self.db.query(Consumables).delete()
                
                # 삽입할 데이터 리스트: 데이터프레임을 딕셔너리 리스트로 변환
                # ex) 
                # [
                #    {'ID': 1, 'Release': 1, 'Name': 'Name1', 'Description': 'Description1', 'Unit_Type': 'Unit_Type1', 'I_Value': 1, 'F_Value': 1, 'Price': 1, 'Unit_Price': 1, 'VAT': 1, 'TaxableType': 'TaxableType1', 'Covered_Type': 'Covered_Type1'}, 
                #    {'ID': 2, 'Release': 1, 'Name': 'Name2', 'Description': 'Description2', 'Unit_Type': 'Unit_Type2', 'I_Value': 2, 'F_Value': 2, 'Price': 2, 'Unit_Price': 2, 'VAT': 2, 'TaxableType': 'TaxableType2', 'Covered_Type': 'Covered_Type2'}
                # ]
                insert_list = used_df.to_dict(orient='records')
                
                # 배치 삽입: bulk_insert_mappings 함수 사용
                # render_nulls라는 인자를 False로 설정하여, NULL 값을 무시하고 삽입할 수 있음 (Optional)
                self.db.bulk_insert_mappings(Consumables, insert_list)
                
            # with self.db.begin(): 트랜잭션 커밋 자동 적용 및 롤백 자동 적용

            print("[DEBUG] Consumables 테이블 삽입 완료")
            
            # 성공 결과 반환
            return self.success_result(len(used_df), len(insert_list))
            
        # 실패 결과 반환
        except Exception as e:
            return self.failure_result(f"삽입 중 오류 발생: {str(e)}")
                