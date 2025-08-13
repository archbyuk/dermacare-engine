"""
InfoMembership Excel 파서
멤버십 정보 테이블 파싱
"""

import pandas as pd
from typing import Tuple, Dict, Any
from ..abstract_parser import AbstractParser
from db.models.info import InfoMembership


class InfoMembershipParser(AbstractParser):
    """멤버십 정보 파서"""
    
    def __init__(self, db_session):
        super().__init__(db_session, "Info_Membership")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, list]:
        """데이터 검증"""
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['ID', 'Release', 'Membership_ID', 'Membership_Name']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼 '{col}'이 없습니다")
        
        if errors:
            return False, errors
        
        # ID 컬럼 검증
        if 'ID' in df.columns:
            # NULL ID는 허용 (무시됨)
            null_ids = df['ID'].isna().sum()
            if null_ids > 0:
                print(f"⚠️ ID 컬럼에 {null_ids}개의 NULL 값이 있습니다 (무시됨)")
        
        # 중복 ID 검증
        if 'ID' in df.columns:
            valid_ids = df[df['ID'].notna()]['ID']
            if valid_ids.duplicated().any():
                errors.append("중복된 ID가 있습니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 정리"""
        # 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # ID 컬럼 정리 (NULL 값 제거)
        if 'ID' in df.columns:
            df = df[df['ID'].notna()].copy()
        
        # 정수 컬럼들 정리
        int_columns = ['ID', 'Release', 'Membership_ID']
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].where(df[col].notna(), None)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """데이터 삽입"""
        try:
            records = []
            for _, row in df.iterrows():
                record = InfoMembership(
                    ID=int(row['ID']) if pd.notna(row['ID']) else None,
                    Release=int(row['Release']) if pd.notna(row['Release']) else None,
                    Membership_ID=int(row['Membership_ID']) if pd.notna(row['Membership_ID']) else None,
                    Membership_Name=str(row['Membership_Name']) if pd.notna(row['Membership_Name']) else None,
                    Membership_Description=str(row['Membership_Description']) if pd.notna(row['Membership_Description']) else None,
                    Precautions=str(row['Precautions']) if pd.notna(row['Precautions']) else None
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
