"""
Product_Standard 테이블용 Excel 파서
표준 상품 데이터를 Excel에서 읽어 DB에 삽입
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from ..abstract_parser import AbstractParser
from db.models.product import ProductStandard


class ProductStandardParser(AbstractParser):
    """표준 상품 테이블 파서"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Product_Standard")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Product_Standard 테이블 데이터 검증
        """
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['ID']
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
        numeric_columns = ['ID', 'Release', 'Element_ID', 'Bundle_ID', 'Sequence_ID',
                          'Product_Info_ID', 'Procedure_Cost', 'Original_Price', 
                          'Sell_Price', 'Margin', 'Validity_Period']
        for col in numeric_columns:
            if col in df.columns:
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    try:
                        pd.to_numeric(df.loc[non_null_mask, col], errors='raise')
                    except (ValueError, TypeError):
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # Float 컬럼 검증
        float_columns = ['Discount_Rate', 'Margin_Rate']
        for col in float_columns:
            if col in df.columns:
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    try:
                        pd.to_numeric(df.loc[non_null_mask, col], errors='raise')
                    except (ValueError, TypeError):
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 참조 관계 검증 (Element_ID, Bundle_ID, Sequence_ID 중 하나는 있어야 함) - 주석 처리
        # 실제 데이터에서는 이 세 컬럼이 모두 NULL일 수 있음
        # ref_columns = ['Element_ID', 'Bundle_ID', 'Sequence_ID']
        # for index, row in df.iterrows():
        #     has_reference = any(
        #         col in df.columns and pd.notna(row.get(col)) and row.get(col) != -1 
        #         for col in ref_columns
        #     )
        #     if not has_reference:
        #         errors.append(f"행 {index + 1}: Element_ID, Bundle_ID, Sequence_ID 중 하나는 필수입니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 정리"""
        # 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # 정수 컬럼들 정리
        int_columns = ['ID', 'Release', 'Element_ID', 'Bundle_ID', 'Custom_ID', 'Sequence_ID',
                      'Standard_Info_ID', 'Procedure_Cost', 'Original_Price', 
                      'Sell_Price', 'Margin', 'Validity_Period']
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # nan 값을 None으로 변환
                df[col] = df[col].replace([pd.NA, pd.NaT, float('nan'), 'nan'], None)
                df[col] = df[col].where(df[col].notna(), None)
        
        # 실수 컬럼들 정리
        float_columns = ['Discount_Rate', 'Margin_Rate']
        for col in float_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # nan 값을 None으로 변환
                df[col] = df[col].replace([pd.NA, pd.NaT, float('nan'), 'nan'], None)
                df[col] = df[col].where(df[col].notna(), None)
        
        # 날짜 컬럼들을 MySQL DATE 타입으로 변환
        date_columns = ['Standard_Start_Date', 'Standard_End_Date']
        df = self.data_cleaner.convert_date_columns_to_mysql_date(df, date_columns)
        
        # 문자열 컬럼들에서 nan 처리
        string_columns = ['Package_Type']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].replace([pd.NA, pd.NaT, float('nan'), 'nan', 'None', 'null'], None)
                df[col] = df[col].where(df[col].notna(), None)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Product_Standard 테이블에 데이터 삽입
        """
        try:
            total_rows = len(df)
            inserted_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # ORM 객체 생성
                    product_standard = ProductStandard(
                        ID=row.get('ID'),
                        Release=row.get('Release'),
                        Package_Type=row.get('Package_Type'),
                        Element_ID=row.get('Element_ID'),
                        Bundle_ID=row.get('Bundle_ID'),
                        Custom_ID=row.get('Custom_ID'),
                        Sequence_ID=row.get('Sequence_ID'),
                        Standard_Info_ID=row.get('Standard_Info_ID'),
                        Procedure_Cost=row.get('Procedure_Cost'),
                        Original_Price=row.get('Original_Price'),
                        Sell_Price=row.get('Sell_Price'),
                        Discount_Rate=row.get('Discount_Rate'),
                        Margin=row.get('Margin'),
                        Margin_Rate=row.get('Margin_Rate'),
                        Standard_Start_Date=row.get('Standard_Start_Date'),
                        Standard_End_Date=row.get('Standard_End_Date'),
                        Validity_Period=row.get('Validity_Period')
                    )
                    
                    # DB에 추가 (REPLACE 방식)
                    existing = self.db.query(ProductStandard).filter(
                        ProductStandard.ID == row.get('ID')
                    ).first()
                    
                    if existing:
                        # 기존 레코드 업데이트
                        for key, value in row.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # 새 레코드 추가
                        self.db.add(product_standard)
                    
                    inserted_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"행 {index + 1}: {str(e)}")
                    continue
            
            # 커밋
            self.db.commit()
            
            return self.result_helper.create_result_dict(
                self.table_name,
                total_rows,
                inserted_count,
                error_count,
                errors if errors else None
            )
            
        except Exception as e:
            self.db.rollback()
            return self.result_helper.create_error_result(
                self.table_name,
                f"삽입 중 오류 발생: {str(e)}"
            )
