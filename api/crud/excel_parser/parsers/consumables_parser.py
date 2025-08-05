"""
    Consumables 테이블 전용 파서
    - 4행 메타데이터 구조 사용 (일반적인 Excel 파싱)
    - 소모품 정보: Name, Description, Unit_Type, I_Value, F_Value, Price, Unit_Price
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
import pandas as pd
from ..abstract_parser import AbstractParser
from ..base import DataCleaner, ResultHelper
from db.models.consumables import Consumables


class ConsumablesParser(AbstractParser):
    """ Consumables 테이블 전용 파서 클래스 """
    
    def __init__(self, db: Session):
        super().__init__("Consumables")
        self.db = db
        self.data_cleaner = DataCleaner()
        self.result_helper = ResultHelper()
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Consumables 테이블 특화 데이터 검증
        - 필수 컬럼: Name
        - 선택 컬럼: Description, Unit_Type, I_Value, F_Value, Price, Unit_Price
        """
        errors = []
        
        # 1. 필수 컬럼 존재 확인
        required_columns = ['Name']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # 2. Name 컬럼 빈 값 확인
        empty_names = df[df['Name'].isna() | (df['Name'].astype(str).str.strip() == '')].index.tolist()
        if empty_names:
            errors.append(f"Name이 비어있는 행들: {[i+1 for i in empty_names[:5]]}")
        
        # 3. 숫자 컬럼 검증
        numeric_columns = ['I_Value', 'F_Value', 'Price', 'Unit_Price']
        for col in numeric_columns:
            if col in df.columns:
                # NaN이 아닌 값들만 숫자인지 확인
                non_null_values = df[col].dropna()
                if not non_null_values.empty:
                    try:
                        pd.to_numeric(non_null_values, errors='raise')
                    except:
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 4. 데이터 길이 검증
        if 'Name' in df.columns:
            long_names = df[df['Name'].astype(str).str.len() > 255].index.tolist()
            if long_names:
                errors.append(f"Name이 255자를 초과하는 행들: {[i+1 for i in long_names[:3]]}")
        
        if 'Unit_Type' in df.columns:
            long_unit_types = df[df['Unit_Type'].astype(str).str.len() > 100].index.tolist()
            if long_unit_types:
                errors.append(f"Unit_Type이 100자를 초과하는 행들: {[i+1 for i in long_unit_types[:3]]}")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Consumables 테이블 특화 데이터 정리
        """
        # 1. 공통 정리 작업
        df = self.data_cleaner.clean_common_data(df)
        
        # 2. 문자열 컬럼 정리
        string_columns = ['Name', 'Description', 'Unit_Type']
        for col in string_columns:
            if col in df.columns:
                # 문자열로 변환하고 공백 제거
                df[col] = df[col].astype(str).str.strip()
                # 'nan', 빈 문자열을 None으로 변환
                df[col] = df[col].replace(['nan', ''], None)
        
        # 3. 숫자 컬럼 정리
        if 'I_Value' in df.columns:
            df['I_Value'] = pd.to_numeric(df['I_Value'], errors='coerce').astype('Int64')
        
        if 'F_Value' in df.columns:
            df['F_Value'] = pd.to_numeric(df['F_Value'], errors='coerce')
        
        if 'Price' in df.columns:
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce').astype('Int64')
        
        if 'Unit_Price' in df.columns:
            df['Unit_Price'] = pd.to_numeric(df['Unit_Price'], errors='coerce').astype('Int64')
        
        # 4. Name이 비어있는 행 제거 (필수 컬럼)
        df = df.dropna(subset=['Name']).reset_index(drop=True)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Consumables 테이블에 데이터 삽입
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
                    if not name:
                        continue
                    
                    existing = self.db.query(Consumables).filter(
                        Consumables.Name == name
                    ).first()
                    
                    if existing:
                        # 기존 데이터 업데이트
                        updated = False
                        
                        if 'Description' in df.columns and pd.notna(row['Description']):
                            desc = str(row['Description']).strip() if row['Description'] != 'None' else None
                            if existing.Description != desc:
                                existing.Description = desc
                                updated = True
                        
                        if 'Unit_Type' in df.columns and pd.notna(row['Unit_Type']):
                            unit_type = str(row['Unit_Type']).strip() if row['Unit_Type'] != 'None' else None
                            if existing.Unit_Type != unit_type:
                                existing.Unit_Type = unit_type
                                updated = True
                        
                        if 'I_Value' in df.columns and pd.notna(row['I_Value']):
                            new_value = int(row['I_Value']) if int(row['I_Value']) != -1 else None
                            if existing.I_Value != new_value:
                                existing.I_Value = new_value
                                updated = True
                        
                        if 'F_Value' in df.columns and pd.notna(row['F_Value']):
                            new_value = float(row['F_Value']) if float(row['F_Value']) != -1 else None
                            if existing.F_Value != new_value:
                                existing.F_Value = new_value
                                updated = True
                        
                        if 'Price' in df.columns and pd.notna(row['Price']):
                            new_value = int(row['Price']) if int(row['Price']) != -1 else None
                            if existing.Price != new_value:
                                existing.Price = new_value
                                updated = True
                        
                        if 'Unit_Price' in df.columns and pd.notna(row['Unit_Price']):
                            new_value = int(row['Unit_Price']) if int(row['Unit_Price']) != -1 else None
                            if existing.Unit_Price != new_value:
                                existing.Unit_Price = new_value
                                updated = True
                        
                        if updated:
                            updated_count += 1
                        inserted_count += 1
                    
                    else:
                        # 새로운 데이터 삽입
                        consumable = Consumables(
                            Name=name,
                            Description=str(row['Description']).strip() if pd.notna(row.get('Description')) and str(row['Description']).strip() != 'None' else None,
                            Unit_Type=str(row['Unit_Type']).strip() if pd.notna(row.get('Unit_Type')) and str(row['Unit_Type']).strip() != 'None' else None,
                            I_Value=int(row['I_Value']) if pd.notna(row.get('I_Value')) and int(row['I_Value']) != -1 else None,
                            F_Value=float(row['F_Value']) if pd.notna(row.get('F_Value')) and float(row['F_Value']) != -1 else None,
                            Price=int(row['Price']) if pd.notna(row.get('Price')) and int(row['Price']) != -1 else None,
                            Unit_Price=int(row['Unit_Price']) if pd.notna(row.get('Unit_Price')) and int(row['Unit_Price']) != -1 else None
                        )
                        self.db.add(consumable)
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
