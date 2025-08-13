"""
Info_Standard 테이블용 Excel 파서
표준 정보 데이터를 Excel에서 읽어 DB에 삽입
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from ..abstract_parser import AbstractParser
from db.models.info import InfoStandard


class InfoStandardParser(AbstractParser):
    """표준 정보 테이블 파서"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Info_Standard")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Info_Standard 테이블 데이터 검증 (ID가 NULL인 행은 제외)
        """
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['ID']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # ID가 NULL이 아닌 행만 필터링
        valid_rows_count = df['ID'].notna().sum()
        if valid_rows_count == 0:
            errors.append("유효한 ID를 가진 행이 없습니다")
            return False, errors
        
        # 유효한 행들만 대상으로 검증
        valid_df = df[df['ID'].notna()]
        
        # ID 중복 확인 (유효한 행들만)
        if valid_df['ID'].duplicated().any():
            duplicated_ids = valid_df[valid_df['ID'].duplicated()]['ID'].tolist()
            errors.append(f"중복된 ID가 있습니다: {duplicated_ids}")
        
        # 숫자 컬럼 검증
        numeric_columns = ['ID', 'Release', 'Product_Standard_ID']
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
        Info_Standard 데이터 정리 (ID가 NULL인 행은 제외)
        """
        # ID가 NULL이 아닌 행만 필터링
        df = df[df['ID'].notna()]
        
        # 기본 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # 숫자 컬럼 타입 변환 (pandas <NA> 문제 해결)
        numeric_columns = ['ID', 'Release', 'Product_Standard_ID']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].where(df[col].notna(), None)
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    df.loc[non_null_mask, col] = pd.to_numeric(df.loc[non_null_mask, col], errors='coerce')
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Info_Standard 테이블에 데이터 삽입
        """
        try:
            total_rows = len(df)
            inserted_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # ORM 객체 생성
                    info_standard = InfoStandard(
                        ID=row.get('ID'),
                        Release=row.get('Release'),
                        Product_Standard_ID=row.get('Product_Standard_ID'),
                        Product_Standard_Name=row.get('Product_Standard_Name'),
                        Product_Standard_Description=row.get('Product_Standard_Description'),
                        Precautions=row.get('Precautions')
                    )
                    
                    # DB에 추가 (REPLACE 방식)
                    existing = self.db.query(InfoStandard).filter(
                        InfoStandard.ID == row.get('ID')
                    ).first()
                    
                    if existing:
                        # 기존 레코드 업데이트
                        for key, value in row.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # 새 레코드 추가
                        self.db.add(info_standard)
                    
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
