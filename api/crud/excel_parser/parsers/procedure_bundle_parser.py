"""
Procedure_Bundle 테이블용 Excel 파서
시술 번들 데이터를 Excel에서 읽어 DB에 삽입 (복합 PK: GroupID, ID)
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from ..abstract_parser import AbstractParser
from db.models.procedure import ProcedureBundle


class ProcedureBundleParser(AbstractParser):
    """시술 번들 테이블 파서 (복합 PK)"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Procedure_Bundle")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Procedure_Bundle 테이블 데이터 검증
        - 복합 PK (GroupID, ID) 검증
        """
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['GroupID', 'ID']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # 복합 PK 컬럼 검증
        for col in ['GroupID', 'ID']:
            if df[col].isnull().any():
                errors.append(f"{col} 컬럼에 NULL 값이 있습니다")
        
        # 복합 PK 중복 확인
        duplicated_mask = df[['GroupID', 'ID']].duplicated()
        if duplicated_mask.any():
            duplicated_pairs = df[duplicated_mask][['GroupID', 'ID']].values.tolist()
            errors.append(f"중복된 (GroupID, ID) 조합이 있습니다: {duplicated_pairs}")
        
        # 숫자 컬럼 검증
        numeric_columns = ['GroupID', 'ID', 'Release', 'Element_ID', 'Element_Cost']
        for col in numeric_columns:
            if col in df.columns:
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    try:
                        pd.to_numeric(df.loc[non_null_mask, col], errors='raise')
                    except (ValueError, TypeError):
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # Float 컬럼 검증
        if 'Price_Ratio' in df.columns:
            non_null_mask = df['Price_Ratio'].notna()
            if non_null_mask.any():
                try:
                    pd.to_numeric(df.loc[non_null_mask, 'Price_Ratio'], errors='raise')
                except (ValueError, TypeError):
                    errors.append("Price_Ratio 컬럼에 숫자가 아닌 값이 있습니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Procedure_Bundle 데이터 정리
        """
        # 기본 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # 숫자 컬럼 타입 변환 (pandas <NA> 문제 해결)
        numeric_columns = ['GroupID', 'ID', 'Release', 'Element_ID', 'Element_Cost']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].where(df[col].notna(), None)
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    df.loc[non_null_mask, col] = pd.to_numeric(df.loc[non_null_mask, col], errors='coerce')
        
        # Float 컬럼 변환
        if 'Price_Ratio' in df.columns:
            df['Price_Ratio'] = df['Price_Ratio'].where(df['Price_Ratio'].notna(), None)
            non_null_mask = df['Price_Ratio'].notna()
            if non_null_mask.any():
                df.loc[non_null_mask, 'Price_Ratio'] = pd.to_numeric(df.loc[non_null_mask, 'Price_Ratio'], errors='coerce')
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Procedure_Bundle 테이블에 데이터 삽입 (복합 PK 처리)
        """
        try:
            total_rows = len(df)
            inserted_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Primary Key 검증: GroupID나 ID가 없으면 건너뛰기
                    if pd.isna(row.get('GroupID')) or pd.isna(row.get('ID')):
                        continue
                    
                    # ORM 객체 생성
                    bundle = ProcedureBundle(
                        GroupID=row.get('GroupID'),
                        ID=row.get('ID'),
                        Release=row.get('Release'),
                        Name=row.get('Name'),
                        Description=row.get('Description'),
                        Element_ID=row.get('Element_ID'),
                        Element_Cost=row.get('Element_Cost'),
                        Price_Ratio=row.get('Price_Ratio')
                    )
                    
                    # DB에 추가 (복합 PK로 REPLACE 방식)
                    existing = self.db.query(ProcedureBundle).filter(
                        ProcedureBundle.GroupID == row.get('GroupID'),
                        ProcedureBundle.ID == row.get('ID')
                    ).first()
                    
                    if existing:
                        # 기존 레코드 업데이트
                        for key, value in row.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # 새 레코드 추가
                        self.db.add(bundle)
                    
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
