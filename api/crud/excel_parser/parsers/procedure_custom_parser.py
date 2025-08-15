"""
ProcedureCustom Excel 파서
커스텀 시술 테이블 파싱
"""

import pandas as pd
from typing import Tuple, Dict, Any
from ..abstract_parser import AbstractParser
from db.models.procedure import ProcedureCustom


class ProcedureCustomParser(AbstractParser):
    """커스텀 시술 파서"""
    
    def __init__(self, db_session):
        super().__init__(db_session, "Procedure_Custom")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, list]:
        """데이터 검증"""
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['GroupID', 'ID', 'Release', 'Name', 'Element_ID']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼 '{col}'이 없습니다")
        
        if errors:
            return False, errors
        
        # 복합 기본키 중복 검증
        if 'GroupID' in df.columns and 'ID' in df.columns:
            duplicated_mask = df.duplicated(subset=['GroupID', 'ID'], keep=False)
            if duplicated_mask.any():
                duplicates = df[duplicated_mask][['GroupID', 'ID']].drop_duplicates()
                error_msg = f"중복된 (GroupID, ID) 조합이 있습니다: {duplicates.values.tolist()}"
                errors.append(error_msg)
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 정리"""
        # 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # 정수 컬럼들 정리
        int_columns = ['GroupID', 'ID', 'Release', 'Element_ID', 'Custom_Count', 'Element_Limit', 'Element_Cost']
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].where(df[col].notna(), None)
        
        # 실수 컬럼들 정리
        float_columns = ['Price_Ratio']
        for col in float_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].where(df[col].notna(), None)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """데이터 삽입"""
        try:
            records = []
            for _, row in df.iterrows():
                record = ProcedureCustom(
                    GroupID=int(row['GroupID']) if pd.notna(row['GroupID']) else None,
                    ID=int(row['ID']) if pd.notna(row['ID']) else None,
                    Release=int(row['Release']) if pd.notna(row['Release']) else None,
                    Name=str(row['Name']) if pd.notna(row['Name']) else None,
                    Description=str(row['Description']) if pd.notna(row['Description']) else None,
                    Element_ID=int(row['Element_ID']) if pd.notna(row['Element_ID']) else None,
                    Custom_Count=int(row['Custom_Count']) if pd.notna(row['Custom_Count']) else None,
                    Element_Limit=int(row['Element_Limit']) if pd.notna(row['Element_Limit']) else None,
                    Element_Cost=int(row['Element_Cost']) if pd.notna(row['Element_Cost']) else None,
                    Price_Ratio=float(row['Price_Ratio']) if pd.notna(row['Price_Ratio']) else None
                )
                records.append(record)
            
            # 배치 삽입
            self.db.add_all(records)
            self.db.commit()
            
            return self.result_helper.create_success_result(
                self.table_name,
                len(records),
                len(records)
            )
            
        except Exception as e:
            self.db.rollback()
            return self.result_helper.create_error_result(
                self.table_name,
                f"데이터 삽입 실패: {str(e)}"
            )
