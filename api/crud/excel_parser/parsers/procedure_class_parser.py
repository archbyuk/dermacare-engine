"""
Procedure_Class 테이블용 Excel 파서
시술 분류 데이터를 Excel에서 읽어 DB에 삽입 (복합 PK: GroupID, ID)
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from ..abstract_parser import AbstractParser
from db.models.procedure import ProcedureClass


class ProcedureClassParser(AbstractParser):
    """시술 분류 테이블 파서 (복합 PK)"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Procedure_Class")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Procedure_Class 테이블 데이터 검증 (복합 PK 특성 고려)
        """
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['GroupID', 'ID']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # 복합 PK 컬럼 검증 - NULL 값만 체크
        for col in ['GroupID', 'ID']:
            if df[col].isnull().any():
                errors.append(f"{col} 컬럼에 NULL 값이 있습니다")
        
        # 복합 PK 중복 확인은 제거 - 삽입 단계에서 처리
        # (GroupID, ID) 조합의 중복은 복합 기본키의 특성상 허용되어야 함
        
        # 숫자 컬럼 검증
        numeric_columns = ['GroupID', 'ID', 'Release']
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
        Procedure_Class 데이터 정리 (중복 제거 포함)
        """
        # 기본 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # 숫자 컬럼 타입 변환
        numeric_columns = ['GroupID', 'ID', 'Release']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
        
        # 복합 PK 중복 제거 (마지막 값 유지)
        if 'GroupID' in df.columns and 'ID' in df.columns:
            original_count = len(df)
            df = df.drop_duplicates(subset=['GroupID', 'ID'], keep='last')
            removed_count = original_count - len(df)
            if removed_count > 0:
                print(f"DEBUG: Procedure_Class에서 {removed_count}개의 중복된 (GroupID, ID) 조합을 제거했습니다.")
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Procedure_Class 테이블에 데이터 삽입 (복합 PK 처리 - UPSERT 방식)
        """
        try:
            total_rows = len(df)
            inserted_count = 0
            updated_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    group_id = row.get('GroupID')
                    id_val = row.get('ID')
                    
                    # 기존 레코드 확인
                    existing = self.db.query(ProcedureClass).filter(
                        ProcedureClass.GroupID == group_id,
                        ProcedureClass.ID == id_val
                    ).first()
                    
                    if existing:
                        # 기존 레코드 업데이트
                        existing.Release = row.get('Release')
                        existing.Class_Major = row.get('Class_Major')
                        existing.Class_Sub = row.get('Class_Sub')
                        existing.Class_Detail = row.get('Class_Detail')
                        existing.Class_Type = row.get('Class_Type')
                        updated_count += 1
                    else:
                        # 새 레코드 추가
                        proc_class = ProcedureClass(
                            GroupID=group_id,
                            ID=id_val,
                            Release=row.get('Release'),
                            Class_Major=row.get('Class_Major'),
                            Class_Sub=row.get('Class_Sub'),
                            Class_Detail=row.get('Class_Detail'),
                            Class_Type=row.get('Class_Type')
                        )
                        self.db.add(proc_class)
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
                inserted_count=inserted_count + updated_count,  # 총 처리된 행 수
                error_count=error_count,
                errors=errors if errors else None
            )
            
        except Exception as e:
            self.db.rollback()
            return self.result_helper.create_error_result(
                table_name=self.table_name,
                error_message=f"삽입 중 오류 발생: {str(e)}"
            )
