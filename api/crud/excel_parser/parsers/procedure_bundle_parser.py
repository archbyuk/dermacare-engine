"""
    ProcedureBundle 테이블 전용 파서
    - 4행 메타데이터 구조 사용 (일반적인 Excel 파싱)
    - 번들 시술 정보: GroupID, Name, Element_ID, Element_Cost, Price_Ratio 등
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
import pandas as pd
from ..abstract_parser import AbstractParser
from ..base import DataCleaner, ResultHelper
from db.models.procedure_bundle import ProcedureBundle


class ProcedureBundleParser(AbstractParser):
    """ ProcedureBundle 테이블 전용 파서 클래스 """
    
    def __init__(self, db: Session):
        super().__init__("ProcedureBundle")
        self.db = db
        self.data_cleaner = DataCleaner()
        self.result_helper = ResultHelper()
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        ProcedureBundle 테이블 특화 데이터 검증
        - 필수 컬럼: GroupID, Name, Element_ID
        - 선택 컬럼: Element_Cost, Price_Ratio, Description
        """
        errors = []
        
        # 1. 필수 컬럼 존재 확인
        required_columns = ['GroupID', 'Name', 'Element_ID']
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
        
        # 3. 숫자 컬럼 검증
        numeric_columns = ['GroupID', 'Element_ID', 'Element_Cost']
        for col in numeric_columns:
            if col in df.columns:
                non_null_values = df[col].dropna()
                if not non_null_values.empty:
                    try:
                        pd.to_numeric(non_null_values, errors='raise')
                    except:
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 4. Float 컬럼 검증 (Price_Ratio)
        if 'Price_Ratio' in df.columns:
            non_null_values = df['Price_Ratio'].dropna()
            if not non_null_values.empty:
                try:
                    pd.to_numeric(non_null_values, errors='raise')
                except:
                    errors.append("Price_Ratio 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 5. 데이터 길이 검증
        if 'Name' in df.columns:
            long_names = df[df['Name'].astype(str).str.len() > 255].index.tolist()
            if long_names:
                errors.append(f"Name이 255자를 초과하는 행들: {[i+1 for i in long_names[:3]]}")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ProcedureBundle 테이블 특화 데이터 정리
        """
        # 1. 공통 정리 작업
        df = self.data_cleaner.clean_common_data(df)
        
        # 2. 문자열 컬럼 정리
        string_columns = ['Name', 'Description']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace(['nan', ''], None)
        
        # 3. 정수 컬럼 정리
        integer_columns = ['GroupID', 'Element_ID', 'Element_Cost']
        for col in integer_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
        
        # 4. Float 컬럼 정리
        if 'Price_Ratio' in df.columns:
            df['Price_Ratio'] = pd.to_numeric(df['Price_Ratio'], errors='coerce')
        
        # 5. 필수 컬럼이 비어있는 행 제거
        required_columns = ['GroupID', 'Name', 'Element_ID']
        df = df.dropna(subset=required_columns).reset_index(drop=True)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ProcedureBundle 테이블에 데이터 삽입
        """
        total_rows = len(df)
        inserted_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        
        try:
            for index, row in df.iterrows():
                try:
                    # GroupID + Name + Element_ID 조합으로 기존 데이터 확인 (복합 키)
                    group_id = int(row['GroupID'])
                    name = str(row['Name']).strip()
                    element_id = self._get_valid_element_id(row.get('Element_ID'))
                    
                    if not name or name == 'nan' or element_id is None:
                        continue  # 빈 Name이나 유효하지 않은 Element_ID는 건너뛰기
                    
                    existing = self.db.query(ProcedureBundle).filter(
                        ProcedureBundle.GroupID == group_id,
                        ProcedureBundle.Name == name,
                        ProcedureBundle.Element_ID == element_id
                    ).first()
                    
                    # 데이터 준비
                    data = {
                        'GroupID': group_id,
                        'Name': name,
                        'Description': str(row['Description']).strip() if pd.notna(row.get('Description')) and str(row['Description']).strip() != 'None' else None,
                        'Element_ID': element_id,
                        'Element_Cost': int(row['Element_Cost']) if pd.notna(row.get('Element_Cost')) and int(row['Element_Cost']) != -1 else None,
                        'Price_Ratio': float(row['Price_Ratio']) if pd.notna(row.get('Price_Ratio')) and float(row['Price_Ratio']) != -1 else None
                    }
                    
                    if existing:
                        # 기존 데이터 업데이트
                        updated = False
                        for key, value in data.items():
                            if key not in ['GroupID', 'Name', 'Element_ID']:  # 키 필드는 제외
                                if getattr(existing, key) != value:
                                    setattr(existing, key, value)
                                    updated = True
                        
                        if updated:
                            updated_count += 1
                        inserted_count += 1
                    
                    else:
                        # 새로운 데이터 삽입
                        procedure_bundle = ProcedureBundle(**data)
                        self.db.add(procedure_bundle)
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
