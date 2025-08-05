"""
    ProcedureProduct 테이블 전용 파서
    - 4행 메타데이터 구조 사용 (일반적인 Excel 파싱)
    - 최종 시술 상품: Package_Type, Procedure_ID, Price, Sell_Price, Discount_Rate 등
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
import pandas as pd
from ..abstract_parser import AbstractParser
from ..base import DataCleaner, ResultHelper
from db.models.procedure_product import ProcedureProduct


class ProcedureProductParser(AbstractParser):
    """ ProcedureProduct 테이블 전용 파서 클래스 """
    
    def __init__(self, db: Session):
        super().__init__("ProcedureProduct")
        self.db = db
        self.data_cleaner = DataCleaner()
        self.result_helper = ResultHelper()
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        ProcedureProduct 테이블 특화 데이터 검증
        - 필수 컬럼: Package_Type, Procedure_ID
        - 선택 컬럼: Price, Sell_Price, Discount_Rate, Margin, Validity_Period 등
        """
        errors = []
        
        # 1. 필수 컬럼 존재 확인
        required_columns = ['Package_Type', 'Procedure_ID']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # 2. 필수 컬럼 빈 값 확인
        for col in required_columns:
            empty_values = df[df[col].isna() | (df[col].astype(str).str.strip() == '')].index.tolist()
            if empty_values:
                errors.append(f"{col}이 비어있는 행들: {[i+1 for i in empty_values[:5]]}")
        
        # 3. 숫자 컬럼 검증
        numeric_columns = ['Procedure_ID', 'Procedure_Info_ID', 'Procedure_Cost', 'Price', 'Sell_Price', 'Margin', 'Validity_Period']
        for col in numeric_columns:
            if col in df.columns:
                non_null_values = df[col].dropna()
                if not non_null_values.empty:
                    try:
                        pd.to_numeric(non_null_values, errors='raise')
                    except:
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 4. Float 컬럼 검증 (Discount_Rate, Margin_Rate)
        float_columns = ['Discount_Rate', 'Margin_Rate']
        for col in float_columns:
            if col in df.columns:
                non_null_values = df[col].dropna()
                if not non_null_values.empty:
                    try:
                        pd.to_numeric(non_null_values, errors='raise')
                    except:
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 5. 데이터 길이 검증
        if 'Package_Type' in df.columns:
            long_types = df[df['Package_Type'].astype(str).str.len() > 100].index.tolist()
            if long_types:
                errors.append(f"Package_Type이 100자를 초과하는 행들: {[i+1 for i in long_types[:3]]}")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ProcedureProduct 테이블 특화 데이터 정리
        """
        # 1. 공통 정리 작업
        df = self.data_cleaner.clean_common_data(df)
        
        # 2. 문자열 컬럼 정리
        string_columns = ['Package_Type']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace(['nan', ''], None)
        
        # 3. 정수 컬럼 정리
        integer_columns = ['Procedure_ID', 'Procedure_Info_ID', 'Procedure_Cost', 'Price', 'Sell_Price', 'Margin', 'Validity_Period']
        for col in integer_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
        
        # 4. Float 컬럼 정리
        float_columns = ['Discount_Rate', 'Margin_Rate']
        for col in float_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 5. 필수 컬럼이 비어있는 행 제거
        required_columns = ['Package_Type', 'Procedure_ID']
        df = df.dropna(subset=required_columns).reset_index(drop=True)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ProcedureProduct 테이블에 데이터 삽입
        """
        total_rows = len(df)
        inserted_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        
        try:
            for index, row in df.iterrows():
                try:
                    # Package_Type + Procedure_ID 조합으로 기존 데이터 확인 (복합 키)
                    package_type = str(row['Package_Type']).strip()
                    procedure_id = int(row['Procedure_ID'])
                    
                    if not package_type:
                        continue
                    
                    existing = self.db.query(ProcedureProduct).filter(
                        ProcedureProduct.Package_Type == package_type,
                        ProcedureProduct.Procedure_ID == procedure_id
                    ).first()
                    
                    # 데이터 준비
                    data = {
                        'Package_Type': package_type,
                        'Procedure_ID': procedure_id,
                        'Procedure_Info_ID': self._get_valid_procedure_info_id(row.get('Procedure_Info_ID')),
                        'Procedure_Cost': int(row['Procedure_Cost']) if pd.notna(row.get('Procedure_Cost')) and int(row['Procedure_Cost']) != -1 else None,
                        'Price': int(row['Price']) if pd.notna(row.get('Price')) and int(row['Price']) != -1 else None,
                        'Sell_Price': int(row['Sell_Price']) if pd.notna(row.get('Sell_Price')) and int(row['Sell_Price']) != -1 else None,
                        'Discount_Rate': float(row['Discount_Rate']) if pd.notna(row.get('Discount_Rate')) and float(row['Discount_Rate']) != -1 else 0.0,
                        'Margin': int(row['Margin']) if pd.notna(row.get('Margin')) and int(row['Margin']) != -1 else None,
                        'Margin_Rate': float(row['Margin_Rate']) if pd.notna(row.get('Margin_Rate')) and float(row['Margin_Rate']) != -1 else None,
                        'Validity_Period': int(row['Validity_Period']) if pd.notna(row.get('Validity_Period')) and int(row['Validity_Period']) != -1 else None
                    }
                    
                    if existing:
                        # 기존 데이터 업데이트
                        updated = False
                        for key, value in data.items():
                            if key not in ['Package_Type', 'Procedure_ID']:  # 키 필드는 제외
                                if getattr(existing, key) != value:
                                    setattr(existing, key, value)
                                    updated = True
                        
                        if updated:
                            updated_count += 1
                        inserted_count += 1
                    
                    else:
                        # 새로운 데이터 삽입
                        procedure_product = ProcedureProduct(**data)
                        self.db.add(procedure_product)
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
    
    def _get_valid_procedure_info_id(self, procedure_info_id):
        """유효한 ProcedureInfo ID 반환 (Procedure_ID로 매칭, 존재하지 않으면 None)"""
        if pd.isna(procedure_info_id) or procedure_info_id == 0 or procedure_info_id == -1:
            return None
        
        try:
            procedure_id = int(procedure_info_id)
            if procedure_id <= 0:
                return None
                
            # DB에서 해당 Procedure_ID가 존재하는지 확인하고 실제 ID 반환
            from db.models.procedure_info import ProcedureInfo
            existing = self.db.query(ProcedureInfo).filter(ProcedureInfo.Procedure_ID == procedure_id).first()
            return existing.ID if existing else None
        except (ValueError, TypeError):
            return None