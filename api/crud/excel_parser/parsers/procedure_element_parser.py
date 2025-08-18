"""
Procedure_Element 테이블용 Excel 파서
시술 요소 데이터를 Excel에서 읽어 DB에 삽입
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from ..abstract_parser import AbstractParser
from db.models.procedure import ProcedureElement


class ProcedureElementParser(AbstractParser):
    """시술 요소 테이블 파서"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Procedure_Element")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Procedure_Element 테이블 데이터 검증
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
        numeric_columns = ['ID', 'Release', 'Plan_Count', 'Plan_Interval', 'Consum_1_ID', 
                          'Consum_1_Count', 'Procedure_Cost', 'Price']
        for col in numeric_columns:
            if col in df.columns:
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    try:
                        pd.to_numeric(df.loc[non_null_mask, col], errors='raise')
                    except (ValueError, TypeError):
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # Float 컬럼 검증
        if 'Cost_Time' in df.columns:
            non_null_mask = df['Cost_Time'].notna()
            if non_null_mask.any():
                try:
                    pd.to_numeric(df.loc[non_null_mask, 'Cost_Time'], errors='raise')
                except (ValueError, TypeError):
                    errors.append("Cost_Time 컬럼에 숫자가 아닌 값이 있습니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Procedure_Element 데이터 정리
        """
        # 기본 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # Name 컬럼 필수 처리
        if 'Name' in df.columns:
            df['Name'] = df['Name'].fillna('Unknown Procedure')
        
        # 숫자 컬럼 타입 변환 (pandas <NA> 문제 해결)
        numeric_columns = ['ID', 'Release', 'Plan_Count', 'Plan_Interval', 'Consum_1_ID', 
                          'Consum_1_Count', 'Procedure_Cost', 'Price']
        for col in numeric_columns:
            if col in df.columns:
                # pandas <NA>를 None으로 변환 후 숫자 변환
                df[col] = df[col].where(df[col].notna(), None)
                # None이 아닌 값만 숫자로 변환
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    df.loc[non_null_mask, col] = pd.to_numeric(df.loc[non_null_mask, col], errors='coerce')
        
        # Float 컬럼 변환
        if 'Cost_Time' in df.columns:
            df['Cost_Time'] = df['Cost_Time'].where(df['Cost_Time'].notna(), None)
            non_null_mask = df['Cost_Time'].notna()
            if non_null_mask.any():
                df.loc[non_null_mask, 'Cost_Time'] = pd.to_numeric(df.loc[non_null_mask, 'Cost_Time'], errors='coerce')
        
        # Plan_State 컬럼 처리 (boolean → INT 변환)
        if 'Plan_State' in df.columns:
            # pandas <NA>를 None으로 변환
            df['Plan_State'] = df['Plan_State'].where(df['Plan_State'].notna(), None)
            # None이 아닌 값만 숫자로 변환
            non_null_mask = df['Plan_State'].notna()
            if non_null_mask.any():
                df.loc[non_null_mask, 'Plan_State'] = pd.to_numeric(df.loc[non_null_mask, 'Plan_State'], errors='coerce')
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Procedure_Element 테이블에 데이터 삽입
        """
        try:
            total_rows = len(df)
            inserted_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Plan_State 값 처리 (na, nan → None)
                    plan_state = row.get('Plan_State')
                    if pd.isna(plan_state) or str(plan_state).lower() in ['na', 'nan', 'none', '<na>']:
                        plan_state = None
                    elif plan_state is not None:
                        try:
                            plan_state = int(plan_state)
                        except (ValueError, TypeError):
                            plan_state = None
                    
                    # ORM 객체 생성
                    element = ProcedureElement(
                        ID=row.get('ID'),
                        Release=row.get('Release'),
                        Class_Major=row.get('Class_Major'),
                        Class_Sub=row.get('Class_Sub'),
                        Class_Detail=row.get('Class_Detail'),
                        Class_Type=row.get('Class_Type'),
                        Name=row.get('Name'),
                        description=row.get('description'),
                        Position_Type=row.get('Position_Type'),
                        Cost_Time=row.get('Cost_Time'),
                        Plan_State=plan_state,
                        Plan_Count=row.get('Plan_Count'),
                        Plan_Interval=row.get('Plan_Interval'),
                        Consum_1_ID=row.get('Consum_1_ID'),
                        Consum_1_Count=row.get('Consum_1_Count'),
                        Procedure_Level=row.get('Procedure_Level'),
                        Procedure_Cost=row.get('Procedure_Cost'),
                        Price=row.get('Price')
                    )
                    
                    # DB에 추가 (REPLACE 방식)
                    existing = self.db.query(ProcedureElement).filter(
                        ProcedureElement.ID == row.get('ID')
                    ).first()
                    
                    if existing:
                        # 기존 레코드 업데이트
                        for key, value in row.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # 새 레코드 추가
                        self.db.add(element)
                    
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
