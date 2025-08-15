"""
Membership Excel 파서
멤버십 상품 테이블 파싱
"""

import pandas as pd
from typing import Tuple, Dict, Any
from ..abstract_parser import AbstractParser
from db.models.membership import Membership


class MembershipParser(AbstractParser):
    """멤버십 상품 파서"""
    
    def __init__(self, db_session):
        super().__init__(db_session, "Membership")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, list]:
        """데이터 검증"""
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['ID', 'Release', 'Membership_Info_ID', 'Payment_Amount']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼 '{col}'이 없습니다")
        
        if errors:
            return False, errors
        
        # 중복 ID 검증
        if 'ID' in df.columns:
            if df['ID'].duplicated().any():
                errors.append("중복된 ID가 있습니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 정리"""
        # 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # 정수 컬럼들 정리
        int_columns = ['ID', 'Release', 'Membership_Info_ID', 'Payment_Amount', 'Bonus_Point', 'Credit', 
                      'Element_ID', 'Bundle_ID', 'Custom_ID', 'Sequence_ID', 'Validity_Period']
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].where(df[col].notna(), None)
        
        # 실수 컬럼들 정리
        float_columns = ['Discount_Rate']
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
                record = Membership(
                    ID=int(row['ID']) if pd.notna(row['ID']) else None,
                    Release=int(row['Release']) if pd.notna(row['Release']) else None,
                    Membership_Info_ID=int(row['Membership_Info_ID']) if pd.notna(row['Membership_Info_ID']) else None,
                    Payment_Amount=int(row['Payment_Amount']) if pd.notna(row['Payment_Amount']) else None,
                    Bonus_Point=int(row['Bonus_Point']) if pd.notna(row['Bonus_Point']) else None,
                    Credit=int(row['Credit']) if pd.notna(row['Credit']) else None,
                    Discount_Rate=float(row['Discount_Rate']) if pd.notna(row['Discount_Rate']) else None,
                    Package_Type=str(row['Package_Type']) if pd.notna(row['Package_Type']) else None,
                    Element_ID=int(row['Element_ID']) if pd.notna(row['Element_ID']) else None,
                    Bundle_ID=int(row['Bundle_ID']) if pd.notna(row['Bundle_ID']) else None,
                    Custom_ID=int(row['Custom_ID']) if pd.notna(row['Custom_ID']) else None,
                    Sequence_ID=int(row['Sequence_ID']) if pd.notna(row['Sequence_ID']) else None,
                    Validity_Period=int(row['Validity_Period']) if pd.notna(row['Validity_Period']) else None,
                    Release_Start_Date=str(row['Release_Start_Date']) if pd.notna(row['Release_Start_Date']) else None,
                    Release_End_Date=str(row['Release_End_Date']) if pd.notna(row['Release_End_Date']) else None
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
