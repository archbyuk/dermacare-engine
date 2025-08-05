"""
    Global 테이블 전용 파서
    - 4행 메타데이터 구조 사용 (일반적인 Excel 파싱)
    - 글로벌 설정: Doc_Price_Minute (의사 인건비 분당)
    - 매우 간단한 구조의 설정 테이블
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
import pandas as pd
from ..abstract_parser import AbstractParser
from ..base import DataCleaner, ResultHelper
from db.models.global_config import Global


class GlobalParser(AbstractParser):
    """ Global 테이블 전용 파서 클래스 """
    
    def __init__(self, db: Session):
        super().__init__("Global")
        self.db = db
        self.data_cleaner = DataCleaner()
        self.result_helper = ResultHelper()
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Global 테이블 특화 데이터 검증
        - 선택 컬럼: Doc_Price_Minute
        """
        errors = []
        
        # 1. Doc_Price_Minute 컬럼이 있는지 확인
        if 'Doc_Price_Minute' not in df.columns:
            errors.append("Doc_Price_Minute 컬럼이 없습니다")
            return False, errors
        
        # 2. Doc_Price_Minute 숫자 검증
        non_null_values = df['Doc_Price_Minute'].dropna()
        if not non_null_values.empty:
            try:
                pd.to_numeric(non_null_values, errors='raise')
            except:
                errors.append("Doc_Price_Minute 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 3. 음수 값 확인
        negative_values = df[df['Doc_Price_Minute'] < 0].index.tolist()
        if negative_values:
            errors.append(f"Doc_Price_Minute에 음수 값이 있는 행들: {[i+1 for i in negative_values[:3]]}")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Global 테이블 특화 데이터 정리
        """
        # 1. 공통 정리 작업
        df = self.data_cleaner.clean_common_data(df)
        
        # 2. Doc_Price_Minute 숫자 변환
        if 'Doc_Price_Minute' in df.columns:
            df['Doc_Price_Minute'] = pd.to_numeric(df['Doc_Price_Minute'], errors='coerce').astype('Int64')
        
        # 3. Doc_Price_Minute이 비어있는 행 제거
        df = df.dropna(subset=['Doc_Price_Minute']).reset_index(drop=True)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Global 테이블에 데이터 삽입
        - Global 테이블은 설정 테이블로 보통 1개 레코드만 유지
        """
        total_rows = len(df)
        inserted_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        
        try:
            # Global 테이블은 보통 ID=1인 단일 레코드로 관리
            existing_global = self.db.query(Global).first()
            
            if not df.empty:
                # 첫 번째 행의 데이터 사용
                first_row = df.iloc[0]
                doc_price_minute = int(first_row['Doc_Price_Minute']) if pd.notna(first_row['Doc_Price_Minute']) else None
                
                if existing_global:
                    # 기존 레코드 업데이트
                    if existing_global.Doc_Price_Minute != doc_price_minute:
                        existing_global.Doc_Price_Minute = doc_price_minute
                        updated_count = 1
                    inserted_count = 1
                else:
                    # 새 레코드 생성
                    global_config = Global(
                        Doc_Price_Minute=doc_price_minute
                    )
                    self.db.add(global_config)
                    inserted_count = 1
                
                # 커밋
                self.db.commit()
                
                # 여러 행이 있으면 경고 메시지
                if len(df) > 1:
                    errors.append(f"Global 테이블은 단일 설정 레코드만 유지합니다. 첫 번째 행만 사용했습니다 (총 {len(df)}행 중)")
        
        except Exception as e:
            error_count = total_rows
            errors.append(f"데이터 삽입 실패: {str(e)}")
            self.db.rollback()
        
        # 결과 생성
        result = self.result_helper.create_result_dict(
            table_name=self.table_name,
            total_rows=total_rows,
            inserted_count=inserted_count,
            error_count=error_count,
            errors=errors
        )
        
        # 업데이트 정보 추가
        result['updated_count'] = updated_count
        
        return result
