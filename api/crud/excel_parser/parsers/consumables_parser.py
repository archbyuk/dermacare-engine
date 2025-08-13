"""
Consumables 테이블용 Excel 파서
소모품 데이터를 Excel에서 읽어 DB에 삽입
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..abstract_parser import AbstractParser
from db.models.consumables import Consumables


class ConsumablesParser(AbstractParser):
    """소모품 테이블 파서"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Consumables")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Consumables 테이블 데이터 검증
        - 필수 컬럼 존재 확인
        - ID 컬럼 중복 확인
        - 데이터 타입 검증
        """
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['ID', 'Name']
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
        numeric_columns = ['ID', 'Release', 'I_Value', 'Price', 'Unit_Price']
        for col in numeric_columns:
            if col in df.columns:
                # NULL이 아닌 값들이 숫자인지 확인
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    try:
                        pd.to_numeric(df.loc[non_null_mask, col], errors='raise')
                    except (ValueError, TypeError):
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # Float 컬럼 검증
        if 'F_Value' in df.columns:
            non_null_mask = df['F_Value'].notna()
            if non_null_mask.any():
                try:
                    pd.to_numeric(df.loc[non_null_mask, 'F_Value'], errors='raise')
                except (ValueError, TypeError):
                    errors.append("F_Value 컬럼에 숫자가 아닌 값이 있습니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Consumables 데이터 정리
        - 공통 데이터 정리 적용
        - 컬럼별 특화 정리
        """
        # 기본 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # Name 컬럼 특화 정리 (필수 컬럼이므로 NULL 방지)
        if 'Name' in df.columns:
            df['Name'] = df['Name'].fillna('Unknown')
        
        # 숫자 컬럼 타입 변환 (pandas <NA> 문제 해결)
        numeric_columns = ['ID', 'Release', 'I_Value', 'Price', 'Unit_Price']
        for col in numeric_columns:
            if col in df.columns:
                # pandas <NA>를 None으로 변환 후 숫자 변환
                df[col] = df[col].where(df[col].notna(), None)
                # None이 아닌 값만 숫자로 변환
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    df.loc[non_null_mask, col] = pd.to_numeric(df.loc[non_null_mask, col], errors='coerce')
        
        if 'F_Value' in df.columns:
            df['F_Value'] = df['F_Value'].where(df['F_Value'].notna(), None)
            non_null_mask = df['F_Value'].notna()
            if non_null_mask.any():
                df.loc[non_null_mask, 'F_Value'] = pd.to_numeric(df.loc[non_null_mask, 'F_Value'], errors='coerce')
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Consumables 테이블에 데이터 삽입
        """
        try:
            total_rows = len(df)
            inserted_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # ORM 객체 생성
                    consumable = Consumables(
                        ID=row.get('ID'),
                        Release=row.get('Release'),
                        Name=row.get('Name'),
                        Description=row.get('Description'),
                        Unit_Type=row.get('Unit_Type'),
                        I_Value=row.get('I_Value'),
                        F_Value=row.get('F_Value'),
                        Price=row.get('Price'),
                        Unit_Price=row.get('Unit_Price')
                    )
                    
                    # DB에 추가 (REPLACE 방식)
                    existing = self.db.query(Consumables).filter(Consumables.ID == row.get('ID')).first()
                    if existing:
                        # 기존 레코드 업데이트
                        for key, value in row.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # 새 레코드 추가
                        self.db.add(consumable)
                    
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
