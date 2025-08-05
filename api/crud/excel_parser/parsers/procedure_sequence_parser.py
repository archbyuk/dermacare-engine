"""
    ProcedureSequence 테이블 전용 파서
    - 4행 메타데이터 구조 사용 (일반적인 Excel 파싱)
    - 시퀀스 정보: GroupID, Step_Num, Element_ID, Bundle_ID, Procedure_Cost, Price_Ratio
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
import pandas as pd
from ..abstract_parser import AbstractParser
from ..base import DataCleaner, ResultHelper
from db.models.procedure_sequence import ProcedureSequence


class ProcedureSequenceParser(AbstractParser):
    """ ProcedureSequence 테이블 전용 파서 클래스 """
    
    def __init__(self, db: Session):
        super().__init__("ProcedureSequence")
        self.db = db
        self.data_cleaner = DataCleaner()
        self.result_helper = ResultHelper()
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        ProcedureSequence 테이블 특화 데이터 검증
        - 필수 컬럼: GroupID, Step_Num
        - Element_ID 또는 Bundle_ID 중 하나는 반드시 있어야 함
        """
        errors = []
        
        # 1. 필수 컬럼 존재 확인
        required_columns = ['GroupID', 'Step_Num']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # 2. 필수 컬럼 빈 값 확인 (경고만, 에러 아님)
        for col in required_columns:
            empty_values = df[df[col].isna() | (df[col].astype(str).str.strip() == '')].index.tolist()
            if empty_values:
                print(f"⚠️ {col}이 비어있는 행들은 건너뜁니다: {len(empty_values)}개 행")
        
        # 3. Element_ID 또는 Bundle_ID 중 하나는 있어야 함
        if 'Element_ID' in df.columns and 'Bundle_ID' in df.columns:
            # 둘 다 비어있는 행 확인
            both_empty = df[
                (df['Element_ID'].isna() | (df['Element_ID'].astype(str).str.strip() == '')) &
                (df['Bundle_ID'].isna() | (df['Bundle_ID'].astype(str).str.strip() == ''))
            ].index.tolist()
            if both_empty:
                print(f"⚠️ Element_ID와 Bundle_ID가 모두 비어있는 행들은 건너뜁니다: {len(both_empty)}개 행")
        elif 'Element_ID' not in df.columns and 'Bundle_ID' not in df.columns:
            errors.append("Element_ID 또는 Bundle_ID 컬럼 중 하나는 있어야 합니다")
        
        # 4. 숫자 컬럼 검증
        numeric_columns = ['GroupID', 'Step_Num', 'Element_ID', 'Bundle_ID', 'Procedure_Cost']
        for col in numeric_columns:
            if col in df.columns:
                non_null_values = df[col].dropna()
                if not non_null_values.empty:
                    try:
                        pd.to_numeric(non_null_values, errors='raise')
                    except:
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 5. Float 컬럼 검증 (Price_Ratio)
        if 'Price_Ratio' in df.columns:
            non_null_values = df['Price_Ratio'].dropna()
            if not non_null_values.empty:
                try:
                    pd.to_numeric(non_null_values, errors='raise')
                except:
                    errors.append("Price_Ratio 컬럼에 숫자가 아닌 값이 있습니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ProcedureSequence 테이블 특화 데이터 정리
        """
        # 1. 공통 정리 작업
        df = self.data_cleaner.clean_common_data(df)
        
        # 2. 정수 컬럼 정리
        integer_columns = ['GroupID', 'Step_Num', 'Element_ID', 'Bundle_ID', 'Procedure_Cost']
        for col in integer_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
        
        # 3. Float 컬럼 정리
        if 'Price_Ratio' in df.columns:
            df['Price_Ratio'] = pd.to_numeric(df['Price_Ratio'], errors='coerce')
        
        # 4. 필수 컬럼이 비어있는 행 제거
        required_columns = ['GroupID', 'Step_Num']
        df = df.dropna(subset=required_columns).reset_index(drop=True)
        
        # 5. Element_ID와 Bundle_ID가 모두 비어있는 행 제거
        if 'Element_ID' in df.columns and 'Bundle_ID' in df.columns:
            df = df[~(df['Element_ID'].isna() & df['Bundle_ID'].isna())].reset_index(drop=True)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ProcedureSequence 테이블에 데이터 삽입
        """
        total_rows = len(df)
        inserted_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        
        try:
            for index, row in df.iterrows():
                try:
                    # GroupID + Step_Num 조합으로 기존 데이터 확인 (복합 키)
                    group_id = int(row['GroupID'])
                    step_num = int(row['Step_Num'])
                    
                    existing = self.db.query(ProcedureSequence).filter(
                        ProcedureSequence.GroupID == group_id,
                        ProcedureSequence.Step_Num == step_num
                    ).first()
                    
                    # 데이터 준비
                    data = {
                        'GroupID': group_id,
                        'Step_Num': step_num,
                        'Element_ID': self._get_valid_element_id(row.get('Element_ID')),
                        'Bundle_ID': self._get_valid_bundle_id(row.get('Bundle_ID')),
                        'Procedure_Cost': int(row['Procedure_Cost']) if pd.notna(row.get('Procedure_Cost')) and int(row['Procedure_Cost']) != -1 else None,
                        'Price_Ratio': float(row['Price_Ratio']) if pd.notna(row.get('Price_Ratio')) and float(row['Price_Ratio']) != -1 else None
                    }
                    
                    if existing:
                        # 기존 데이터 업데이트
                        updated = False
                        for key, value in data.items():
                            if key not in ['GroupID', 'Step_Num']:  # 키 필드는 제외
                                if getattr(existing, key) != value:
                                    setattr(existing, key, value)
                                    updated = True
                        
                        if updated:
                            updated_count += 1
                        inserted_count += 1
                    
                    else:
                        # 새로운 데이터 삽입
                        procedure_sequence = ProcedureSequence(**data)
                        self.db.add(procedure_sequence)
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
    
    def _get_valid_element_id(self, element_id):
        """유효한 ProcedureElement ID 반환 (존재하지 않으면 None)"""
        if pd.isna(element_id) or element_id == 0 or element_id == -1:
            return None
        
        try:
            element_id = int(element_id)
            if element_id <= 0:
                return None
                
            # DB에서 해당 ID가 존재하는지 확인
            from db.models.procedure_element import ProcedureElement
            existing = self.db.query(ProcedureElement).filter(ProcedureElement.ID == element_id).first()
            return element_id if existing else None
        except (ValueError, TypeError):
            return None
    
    def _get_valid_bundle_id(self, bundle_id):
        """유효한 ProcedureBundle ID 반환 (존재하지 않으면 None)"""
        if pd.isna(bundle_id) or bundle_id == 0 or bundle_id == -1:
            return None
        
        try:
            bundle_id = int(bundle_id)
            if bundle_id <= 0:
                return None
                
            # DB에서 해당 ID가 존재하는지 확인
            from db.models.procedure_bundle import ProcedureBundle
            existing = self.db.query(ProcedureBundle).filter(ProcedureBundle.ID == bundle_id).first()
            return bundle_id if existing else None
        except (ValueError, TypeError):
            return None
