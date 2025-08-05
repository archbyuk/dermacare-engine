"""
    ProcedureElement 테이블 전용 파서
    - 4행 메타데이터 구조 사용 (일반적인 Excel 파싱)
    - 단일 시술 상세 정보: Class_Major, Class_Sub, Name, Position_Type, Cost_Time 등
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
import pandas as pd
from ..abstract_parser import AbstractParser
from ..base import DataCleaner, ResultHelper
from db.models.procedure_element import ProcedureElement


class ProcedureElementParser(AbstractParser):
    """ ProcedureElement 테이블 전용 파서 클래스 """
    
    def __init__(self, db: Session):
        super().__init__("ProcedureElement")
        self.db = db
        self.data_cleaner = DataCleaner()
        self.result_helper = ResultHelper()
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        ProcedureElement 테이블 특화 데이터 검증
        - 필수 컬럼: Name
        - 선택 컬럼: Class_Major, Class_Sub, Class_Detail, Class_Type, Position_Type, Cost_Time 등
        """
        errors = []
        
        # 1. 필수 컬럼 존재 확인
        required_columns = ['Name']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # 2. Name 컬럼 빈 값 확인 (경고만, 에러 아님)
        empty_names = df[df['Name'].isna() | (df['Name'].astype(str).str.strip() == '')].index.tolist()
        if empty_names:
            print(f"⚠️ Name이 비어있는 행들은 건너뜁니다: {len(empty_names)}개 행")
        
        # 3. 숫자 컬럼 검증
        numeric_columns = ['Cost_Time', 'Plan_Count', 'Consum_1_Count', 'Procedure_Cost', 'Base_Price']
        for col in numeric_columns:
            if col in df.columns:
                non_null_values = df[col].dropna()
                if not non_null_values.empty:
                    try:
                        pd.to_numeric(non_null_values, errors='raise')
                    except:
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 4. Boolean 컬럼 검증 (Plan_State)
        if 'Plan_State' in df.columns:
            non_null_values = df['Plan_State'].dropna()
            if not non_null_values.empty:
                invalid_bool = non_null_values[~non_null_values.isin([0, 1, True, False, '0', '1', 'true', 'false', 'True', 'False'])]
                if not invalid_bool.empty:
                    errors.append("Plan_State 컬럼에 Boolean이 아닌 값이 있습니다")
        
        # 5. 데이터 길이 검증
        string_cols_limits = {
            'Name': 255,
            'Class_Major': 100,
            'Class_Sub': 100,
            'Class_Detail': 100,
            'Class_Type': 100,
            'Position_Type': 100
        }
        
        for col, limit in string_cols_limits.items():
            if col in df.columns:
                long_values = df[df[col].astype(str).str.len() > limit].index.tolist()
                if long_values:
                    errors.append(f"{col}이 {limit}자를 초과하는 행들: {[i+1 for i in long_values[:3]]}")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ProcedureElement 테이블 특화 데이터 정리
        """
        # 1. 공통 정리 작업
        df = self.data_cleaner.clean_common_data(df)
        
        # 2. 문자열 컬럼 정리
        string_columns = ['Name', 'Description', 'Class_Major', 'Class_Sub', 'Class_Detail', 'Class_Type', 'Position_Type']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace(['nan', ''], None)
        
        # 3. 숫자 컬럼 정리
        integer_columns = ['Cost_Time', 'Plan_Count', 'Consum_1_ID', 'Consum_1_Count', 'Procedure_Cost', 'Base_Price']
        for col in integer_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
        
        # 4. Boolean 컬럼 정리
        if 'Plan_State' in df.columns:
            # Boolean 값으로 변환 (1, '1', 'true', 'True' -> True, 나머지 -> False)
            df['Plan_State'] = df['Plan_State'].apply(
                lambda x: x in [1, '1', 'true', 'True', True] if pd.notna(x) else False
            )
        
        # 5. Name이 비어있는 행 제거 (필수 컬럼)
        df = df.dropna(subset=['Name']).reset_index(drop=True)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ProcedureElement 테이블에 데이터 삽입
        """
        total_rows = len(df)
        inserted_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        
        try:
            for index, row in df.iterrows():
                try:
                    # Name으로 기존 데이터 확인 (중복 방지)
                    name = str(row['Name']).strip()
                    if not name or name == 'nan':
                        continue  # 빈 Name은 건너뛰기
                    
                    existing = self.db.query(ProcedureElement).filter(
                        ProcedureElement.Name == name
                    ).first()
                    
                    # 데이터 준비
                    data = {
                        'Class_Major': str(row['Class_Major']).strip() if pd.notna(row.get('Class_Major')) and str(row['Class_Major']).strip() != 'None' else None,
                        'Class_Sub': str(row['Class_Sub']).strip() if pd.notna(row.get('Class_Sub')) and str(row['Class_Sub']).strip() != 'None' else None,
                        'Class_Detail': str(row['Class_Detail']).strip() if pd.notna(row.get('Class_Detail')) and str(row['Class_Detail']).strip() != 'None' else None,
                        'Class_Type': str(row['Class_Type']).strip() if pd.notna(row.get('Class_Type')) and str(row['Class_Type']).strip() != 'None' else None,
                        'Description': str(row['Description']).strip() if pd.notna(row.get('Description')) and str(row['Description']).strip() != 'None' else None,
                        'Position_Type': str(row['Position_Type']).strip() if pd.notna(row.get('Position_Type')) and str(row['Position_Type']).strip() != 'None' else None,
                        'Cost_Time': int(row['Cost_Time']) if pd.notna(row.get('Cost_Time')) and int(row['Cost_Time']) != -1 else None,
                        'Plan_State': bool(row.get('Plan_State', False)),
                        'Plan_Count': int(row['Plan_Count']) if pd.notna(row.get('Plan_Count')) and int(row['Plan_Count']) != -1 else 1,
                        'Consum_1_ID': self._get_valid_consumable_id(row.get('Consum_1_ID')),
                        'Consum_1_Count': int(row['Consum_1_Count']) if pd.notna(row.get('Consum_1_Count')) and int(row['Consum_1_Count']) != -1 else 1,
                        'Procedure_Cost': int(row['Procedure_Cost']) if pd.notna(row.get('Procedure_Cost')) and int(row['Procedure_Cost']) != -1 else None,
                        'Base_Price': int(row['Base_Price']) if pd.notna(row.get('Base_Price')) and int(row['Base_Price']) != -1 else None
                    }
                    
                    if existing:
                        # 기존 데이터 업데이트
                        updated = False
                        for key, value in data.items():
                            if getattr(existing, key) != value:
                                setattr(existing, key, value)
                                updated = True
                        
                        if updated:
                            updated_count += 1
                        inserted_count += 1
                    
                    else:
                        # 새로운 데이터 삽입
                        procedure_element = ProcedureElement(Name=name, **data)
                        self.db.add(procedure_element)
                        inserted_count += 1
                    
                    # 매 50개마다 커밋
                    if (index + 1) % 50 == 0:
                        self.db.commit()
                
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 1}: {str(e)}")
                    self.db.rollback()
            
            # 최종 커밋
            self.db.commit()
        
        except Exception as e:
            error_count = total_rows
            errors.append(f"최종 커밋 실패: {str(e)}")
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
    
    def _get_valid_consumable_id(self, consumable_id):
        """유효한 Consumable ID 반환 (존재하지 않으면 None)"""
        if pd.isna(consumable_id) or consumable_id == 0 or consumable_id == -1:
            return None
        
        try:
            consumable_id = int(consumable_id)
            if consumable_id <= 0:
                return None
                
            # DB에서 해당 ID가 존재하는지 확인
            from db.models.consumables import Consumables
            existing = self.db.query(Consumables).filter(Consumables.ID == consumable_id).first()
            return consumable_id if existing else None
        except (ValueError, TypeError):
            return None
