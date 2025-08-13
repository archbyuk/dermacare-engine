"""
Global 테이블용 Excel 파서
전역 설정 데이터를 Excel에서 읽어 DB에 삽입
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from ..abstract_parser import AbstractParser
from db.models.global_config import Global


class GlobalParser(AbstractParser):
    """전역 설정 테이블 파서"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Global")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Global 테이블 데이터 검증
        - 필수 컬럼 존재 확인
        - ID 컬럼 중복 확인
        - 숫자 컬럼 검증
        """
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['ID']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # ID 컬럼 검증
        if df['ID'].isnull().any():
            errors.append("ID 컬럼에 NULL 값이 있습니다")
        
        # ID 중복 확인
        if df['ID'].duplicated().any():
            duplicated_ids = df[df['ID'].duplicated()]['ID'].tolist()
            errors.append(f"중복된 ID가 있습니다: {duplicated_ids}")
        
        # 숫자 컬럼 검증
        numeric_columns = ['ID', 'Doc_Price_Minute', 'Aesthetician_Price_Minute']
        for col in numeric_columns:
            if col in df.columns:
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    try:
                        pd.to_numeric(df.loc[non_null_mask, col], errors='raise')
                    except (ValueError, TypeError):
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Global 데이터 정리
        - 공통 데이터 정리 적용
        - 숫자 컬럼 타입 변환
        """
        # 기본 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # 숫자 컬럼 타입 변환
        numeric_columns = ['ID', 'Doc_Price_Minute', 'Aesthetician_Price_Minute']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Global 테이블에 데이터 삽입
        """
        try:
            total_rows = len(df)
            inserted_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # ORM 객체 생성
                    global_config = Global(
                        ID=row.get('ID'),
                        Doc_Price_Minute=row.get('Doc_Price_Minute'),
                        Aesthetician_Price_Minute=row.get('Aesthetician_Price_Minute')
                    )
                    
                    # DB에 추가 (REPLACE 방식)
                    existing = self.db.query(Global).filter(Global.ID == row.get('ID')).first()
                    if existing:
                        # 기존 레코드 업데이트
                        existing.Doc_Price_Minute = row.get('Doc_Price_Minute')
                        existing.Aesthetician_Price_Minute = row.get('Aesthetician_Price_Minute')
                    else:
                        # 새 레코드 추가
                        self.db.add(global_config)
                    
                    inserted_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"행 {index + 1}: {str(e)}")
                    continue
            
            # 커밋
            self.db.commit()
            
            return self.result_helper.create_result_dict(
                table_name=self.table_name,
                total_rows=total_rows,
                inserted_count=inserted_count,
                error_count=error_count,
                errors=errors if errors else None
            )
            
        except Exception as e:
            self.db.rollback()
            return self.result_helper.create_error_result(
                table_name=self.table_name,
                error_message=f"삽입 중 오류 발생: {str(e)}"
            )
