"""
    [ 파일 파싱 관련 공통 유틸리티 ]
"""

from typing import Tuple, List, Dict, Any
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
import pandas as pd
from ..utils.cleaner_utils import normalize_data

class AbstractUtils(ABC):
    
    def __init__(self, db_session: Session, table_name: str):
        self.db = db_session
        self.table_name = table_name

    # 각 테이블별 파서의 공통 메서드 정의
    @abstractmethod
    def validate_data(self, used_df: pd.DataFrame, filename: str) -> Tuple[bool, List[str]]:
        """
            [ 데이터 검증 로직 ]
                데이터프레임(used_df)을 검사해서, 필수 컬럼이 있는지 /
                    NULL이나 중복이 있는지 / 
                        숫자 컬럼이 제대로 숫자인지 등을 확인하고 / 
                            결과(성공 여부와 에러 메시지)를 반환하는 함수
            
            Params: used_df
                빈 값, 사용하지 않는 컬럼, 숫자 값이 정리된 데이터프레임 (type: pd.DataFrame)
                
            Return:
                Tuple[bool, List[str]]: (검증 성공 여부, 에러 메시지 리스트)
        """
        
        pass

    def clean_data(self, used_df: pd.DataFrame) -> pd.DataFrame:
        """
            데이터 정리 로직
            각 파서에서 테이블별 특화 정리 구현
            
            Args:
                used_df: 빈 값, 사용하지 않는 컬럼, 숫자 값이 정리된 데이터프레임 (type: pd.DataFrame)
                
            Returns:
                pd.DataFrame: 정리된 DataFrame
        """

        # 결측치 처리, 데이터 타입 변환, 공백 제거, dtypes object로 변환
        return normalize_data(used_df)


    @abstractmethod
    def insert_data(self, used_df: pd.DataFrame) -> Dict[str, Any]:
        """
            DB 삽입 로직
            각 파서에서 테이블별 특화 삽입 구현
            
            Args:
                used_df: 빈 값, 사용하지 않는 컬럼, 숫자 값이 정리된 데이터프레임 (type: pd.DataFrame)
                
            Returns:
                Dict[str, Any]: 삽입 결과 (표준 형식)
        """

        pass

    # insert_data 함수 성공 시 반환 결과
    def success_result(self, total_rows: int, inserted_count: int) -> Dict[str, Any]:
        """
            성공 결과 생성

            self.db.begin() 트랜잭션 시작

            if 트랜잭션 성공 시:
                self.db.commit() 트랜잭션 자동 커밋
                success_result 함수 사용
        """

        return {
            "success": True,
            "table_name": self.table_name,
            "total_rows": total_rows,
            "inserted_count": inserted_count,
            "error_count": 0,
            "errors": None
        }
    
    # insert_data 함수 실패 시 반환 결과
    def failure_result(self, error_message: str) -> Dict[str, Any]:
        """
            실패 결과 생성

            if 트랜잭션 실패 시:
                self.db.rollback() 트랜잭션 자동 롤백
                error_result 함수 사용
        """

        return {
            "success": False,
            "table_name": self.table_name,
            "error": error_message,
            "total_rows": 0,
            "inserted_count": 0,
            "error_count": 1
        }
    