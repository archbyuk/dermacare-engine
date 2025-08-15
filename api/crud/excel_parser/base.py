"""
    공통 데이터 정리 및 유틸리티 함수들
    모든 파서에서 사용할 수 있는 공통 기능 제공
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, date


class DataCleaner:
    """ 데이터 정리 전용 클래스 """
    
    @staticmethod
    def clean_common_data(df: pd.DataFrame) -> pd.DataFrame:
        """
            공통 데이터 정리 작업
            모든 파서에서 사용할 수 있는 기본 정리 로직
        """
        # pandas NA/NaN 값을 Python None으로 변환 (SQLAlchemy 호환성)
        df = df.where(pd.notnull(df), None)
        
        # pandas <NA> 값을 None으로 변환
        for col in df.columns:
            if df[col].dtype == 'object':
                # 문자열 컬럼의 <NA> 처리
                df[col] = df[col].where(df[col].notna(), None)
            elif str(df[col].dtype).startswith('Int') or str(df[col].dtype).startswith('Float'):
                # nullable integer/float의 <NA> 처리
                df[col] = df[col].where(df[col].notna(), None)
        
        # -1 값을 None으로 변환 (모든 컬럼에 적용)
        df = df.replace(-1, None)
        
        # 문자열 컬럼의 앞뒤 공백 제거
        string_columns = df.select_dtypes(include=['object']).columns
        for col in string_columns:
            # None이 아닌 값만 문자열 처리
            mask = df[col].notna()
            if mask.any():
                df.loc[mask, col] = df.loc[mask, col].astype(str).str.strip()
                # 빈 문자열을 None으로 변환
                df[col] = df[col].replace('', None)
                df[col] = df[col].replace('nan', None)
                df[col] = df[col].replace('<NA>', None)
                # 문자열 '-1'도 None으로 변환
                df[col] = df[col].replace('-1', None)
        
        # 모든 컬럼의 pandas 특수값을 Python 기본 타입으로 변환
        for col in df.columns:
            # pandas nullable 타입을 일반 타입으로 변환하되 None은 유지
            if str(df[col].dtype).startswith('Int'):
                df[col] = df[col].astype(object).where(df[col].notna(), None)
            elif str(df[col].dtype).startswith('Float'):
                df[col] = df[col].astype(object).where(df[col].notna(), None)
        
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
    
    @staticmethod
    def convert_excel_date_to_date(excel_date_value: Any) -> Optional[date]:
        """
        Excel 날짜 직렬화 숫자 또는 날짜 문자열을 Python date 객체로 변환
        
        Args:
            excel_date_value: Excel에서 읽은 날짜 값 (숫자, 문자열, 또는 datetime)
            
        Returns:
            date 객체 또는 None (변환 실패 시)
        """
        try:
            # None이나 빈 값 처리
            if excel_date_value is None or str(excel_date_value).strip() == '':
                return None
            
            # 이미 date 객체인 경우
            if isinstance(excel_date_value, date):
                return excel_date_value
            
            # 이미 datetime 객체인 경우
            if isinstance(excel_date_value, datetime):
                return excel_date_value.date()
            
            # 문자열인 경우 다양한 형식 시도
            if isinstance(excel_date_value, str):
                # 'YYYY-MM-DD HH:MM:SS' 형식 처리
                if ' ' in excel_date_value:
                    excel_date_value = excel_date_value.split(' ')[0]
                
                # 'YYYY-MM-DD' 형식 처리
                if '-' in excel_date_value:
                    return datetime.strptime(excel_date_value, '%Y-%m-%d').date()
                
                # 숫자 문자열인 경우 Excel 날짜로 처리
                try:
                    excel_date_value = float(excel_date_value)
                except ValueError:
                    return None
            
            # 숫자인 경우 Excel 날짜로 처리
            if isinstance(excel_date_value, (int, float)):
                # Excel 날짜 기준: 1900년 1월 1일 = 1
                excel_epoch = datetime(1899, 12, 30)  # Excel의 기준점 (1900-01-01 = 1이므로 하루 빼기)
                converted_date = excel_epoch + pd.Timedelta(days=excel_date_value)
                return converted_date.date()
            
            return None
            
        except (ValueError, TypeError, OverflowError):
            # 변환 실패 시 None 반환
            return None
    
    @staticmethod
    def convert_date_columns(df: pd.DataFrame, date_columns: List[str]) -> pd.DataFrame:
        """
        지정된 컬럼들을 Excel 날짜에서 date 객체로 변환
        
        Args:
            df: DataFrame
            date_columns: 날짜 변환할 컬럼명 리스트
            
        Returns:
            변환된 DataFrame
        """
        df_copy = df.copy()
        
        for col in date_columns:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(DataCleaner.convert_excel_date_to_date)
        
        return df_copy
    
    @staticmethod
    def convert_date_columns_to_mysql_date(df: pd.DataFrame, date_columns: List[str]) -> pd.DataFrame:
        """
        지정된 컬럼들을 MySQL DATE 타입으로 변환
        
        Args:
            df: DataFrame
            date_columns: 날짜 변환할 컬럼명 리스트
            
        Returns:
            변환된 DataFrame (날짜는 'YYYY-MM-DD' 형식의 문자열)
        """
        df_copy = df.copy()
        
        for col in date_columns:
            if col in df_copy.columns:
                # 먼저 date 객체로 변환
                df_copy[col] = df_copy[col].apply(DataCleaner.convert_excel_date_to_date)
                # date 객체를 'YYYY-MM-DD' 형식의 문자열로 변환
                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%Y-%m-%d') if x else None)
        
        return df_copy


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
    def create_success_result(table_name: str, total_rows: int, inserted_count: int) -> Dict[str, Any]:
        """ 성공 결과 생성 """
        return {
            "success": True,
            "table_name": table_name,
            "total_rows": total_rows,
            "inserted_count": inserted_count,
            "error_count": 0,
            "errors": None
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