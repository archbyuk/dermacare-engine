"""
    공통 데이터 정리 및 유틸리티 함수들
    모든 파서에서 사용할 수 있는 공통 기능 제공
"""

import pandas as pd
from typing import List, Dict, Any


class DataCleaner:
    """ 데이터 정리 전용 클래스 """
    
    @staticmethod
    def clean_common_data(df: pd.DataFrame) -> pd.DataFrame:
        """
            공통 데이터 정리 작업
            모든 파서에서 사용할 수 있는 기본 정리 로직
        """
        # NaN 값을 None으로 변환
        df = df.where(pd.notnull(df), None)
        
        # 문자열 컬럼의 앞뒤 공백 제거
        string_columns = df.select_dtypes(include=['object']).columns
        for col in string_columns:
            df[col] = df[col].astype(str).str.strip()
            # 빈 문자열을 None으로 변환
            df[col] = df[col].replace('', None)
            df[col] = df[col].replace('nan', None)
        
        return df
    
    @staticmethod
    def remove_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
        """ 빈 행 제거 """
        return df.dropna(how='all').reset_index(drop=True)
    
    @staticmethod
    def strip_column_names(df: pd.DataFrame) -> pd.DataFrame:
        """ 컬럼명 공백 제거 """
        df.columns = df.columns.str.strip()
        return df


class ResultHelper:
    """ 결과 생성 및 처리 전용 클래스 """
    
    @staticmethod
    def create_result_dict(table_name: str, total_rows: int, inserted_count: int, 
                          error_count: int, errors: List[str] = None) -> Dict[str, Any]:
        """
            결과 딕셔너리 생성 (표준 형식)
            모든 파서에서 동일한 형식으로 결과 반환
            
            Args:
                table_name: 테이블명
                total_rows: 총 행 수
                inserted_count: 삽입된 행 수
                error_count: 에러 발생 행 수
                errors: 에러 메시지 리스트
                
            Returns:
                표준 형식의 결과 딕셔너리
        """
        return {
            "success": error_count == 0,
            "table_name": table_name,
            "total_rows": total_rows,
            "inserted_count": inserted_count,
            "error_count": error_count,
            "errors": errors if errors else None
        }
    
    @staticmethod
    def create_error_result(table_name: str, error_message: str) -> Dict[str, Any]:
        """ 에러 결과 생성 """
        return {
            "success": False,
            "table_name": table_name,
            "error": error_message,
            "total_rows": 0,
            "inserted_count": 0,
            "error_count": 1
        }