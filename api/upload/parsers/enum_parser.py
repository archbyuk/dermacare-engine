"""
    [ Enum Parser ]
        열거형 데이터를 DataFrame을 읽어 DB에 삽입하는 파서
        - 복합 키: enum_type, id
        - 각 열이 다른 enum_type, 행이 ID와 name을 나타냄
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from ..utils.abstract_utils import AbstractUtils
from db.models.enum import Enum


class EnumParser(AbstractUtils):
    """
        params:
            used_df: 빈 값, 사용하지 않는 컬럼, 숫자 값이 정리된 데이터프레임 (type: pd.DataFrame)
    """

    def __init__(self, db_session: Session):
        super().__init__(db_session, "Enum")
    
    
    # 필수 컬럼: enum_type, id, name
    def validate_data(self, used_df: pd.DataFrame, filename: str) -> Tuple[bool, List[str]]:
        
        # 에러를 담을 리스트
        errors = []

        # 필수 컬럼 리스트
        required_columns = ['enum_type', 'id', 'name']
        
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
        

        # 복합 PK 중복 확인
        duplicated_pk = used_df[
            ['enum_type', 'id']
        ].duplicated()  # 두 컬럼을 기준으로, 앞에 이미 같은 조합이 있다면 True 반환
        
        # duplicated_pk에 True가 있다면, (중복 O)
        if duplicated_pk.any():
            duplicated_pairs = used_df[duplicated_pk][
                ['enum_type', 'id']
            ].values.tolist()   # 중복된 컬럼을 리스트로 변환
            
            errors.append(f"{filename}의 중복된 (enum_type, id) 조합이 있습니다: {duplicated_pairs}")
    
        print("[DEBUG] Enum 검증 결과: ", errors)
        # 에러 리스트에 아무것도 없다면 0, 아니면 1. 그리고 에러 리스트 반환
        return len(errors) == 0, errors

    
    # Enum 테이블에 데이터 삽입 (DB insert)
    def insert_data(self, used_df: pd.DataFrame) -> Dict[str, Any]:
        
        try:
            # 트랜잭션 시작
            with self.db.begin():
                # 기존 데이터 전체 삭제
                self.db.query(Enum).delete()

                # 삽입할 데이터 리스트: 데이터프레임을 딕셔너리 리스트로 변환
                # ex) 
                # [
                #    {'enum_type': 'enum_type1', 'id': 1, 'name': 'name1'}, 
                #    {'enum_type': 'enum_type2', 'id': 2, 'name': 'name2'}
                # ]
                insert_list = used_df.to_dict(orient='records')

                # 배치 삽입: bulk_insert_mappings 함수 사용
                # render_nulls라는 인자를 False로 설정하여, NULL 값을 무시하고 삽입할 수 있음 (Optional)
                self.db.bulk_insert_mappings(Enum, insert_list)

            # with self.db.begin(): 트랜잭션 커밋 자동 적용 및 롤백 자동 적용

            print(f"[DEBUG] Enum 삽입 완료 - 총 {len(insert_list)}개 항목 삽입됨. 예시:", insert_list[:10])
            
            # 성공 결과 반환
            return self.success_result(len(used_df), len(insert_list))
            
        # 실패 결과 반환
        except Exception as e:
            return self.failure_result(f"삽입 중 오류 발생: {str(e)}")