"""
Procedure_Sequence 테이블용 Excel 파서
시술 순서 데이터를 Excel에서 읽어 DB에 삽입 (복합 PK: GroupID, ID)
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from ..abstract_parser import AbstractParser
from db.models.procedure import ProcedureSequence


class ProcedureSequenceParser(AbstractParser):
    """시술 순서 테이블 파서 (복합 PK)"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Procedure_Sequence")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Procedure_Sequence 테이블 데이터 검증
        """
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['GroupID', 'ID']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # 복합 PK 컬럼 검증 - NULL 값이 있는 행은 제거
        print(f"DEBUG: Procedure_Sequence 검증 - 총 {len(df)}개 행")
        print(f"DEBUG: GroupID NULL 개수: {df['GroupID'].isnull().sum()}")
        print(f"DEBUG: ID NULL 개수: {df['ID'].isnull().sum()}")
        
        # NULL 값이 있는 행 제거
        df = df.dropna(subset=['GroupID', 'ID']).reset_index(drop=True)
        print(f"DEBUG: NULL 제거 후 {len(df)}개 행")
        
        if df.empty:
            errors.append("유효한 데이터가 없습니다 (모든 행에 NULL 값이 있음)")
            return False, errors
        
        # 복합 PK 중복 확인
        duplicated_mask = df[['GroupID', 'ID']].duplicated()
        if duplicated_mask.any():
            duplicated_pairs = df[duplicated_mask][['GroupID', 'ID']].values.tolist()
            errors.append(f"중복된 (GroupID, ID) 조합이 있습니다: {duplicated_pairs}")
        
        # 숫자 컬럼 검증
        numeric_columns = ['GroupID', 'ID', 'Release', 'Step_Num', 'Element_ID', 
                          'Bundle_ID', 'Sequence_Interval', 'Procedure_Cost']
        for col in numeric_columns:
            if col in df.columns:
                non_null_mask = df[col].notna()
                if non_null_mask.any():
                    try:
                        pd.to_numeric(df.loc[non_null_mask, col], errors='raise')
                    except (ValueError, TypeError):
                        errors.append(f"{col} 컬럼에 숫자가 아닌 값이 있습니다")
        
        # Float 컬럼 검증
        if 'Price_Ratio' in df.columns:
            non_null_mask = df['Price_Ratio'].notna()
            if non_null_mask.any():
                try:
                    pd.to_numeric(df.loc[non_null_mask, 'Price_Ratio'], errors='raise')
                except (ValueError, TypeError):
                    errors.append("Price_Ratio 컬럼에 숫자가 아닌 값이 있습니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 정리"""
        # 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        
        # 정수 컬럼들 정리
        int_columns = ['GroupID', 'ID', 'Release', 'Step_Num', 'Element_ID', 
                      'Bundle_ID', 'Custom_ID', 'Sequence_Interval', 'Procedure_Cost']
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # nan 값을 None으로 변환
                df[col] = df[col].replace([pd.NA, pd.NaT, float('nan'), 'nan'], None)
                df[col] = df[col].where(df[col].notna(), None)
        
        # 실수 컬럼들 정리
        if 'Price_Ratio' in df.columns:
            df['Price_Ratio'] = pd.to_numeric(df['Price_Ratio'], errors='coerce')
            # nan 값을 None으로 변환
            df['Price_Ratio'] = df['Price_Ratio'].replace([pd.NA, pd.NaT, float('nan'), 'nan'], None)
            df['Price_Ratio'] = df['Price_Ratio'].where(df['Price_Ratio'].notna(), None)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Procedure_Sequence 테이블에 데이터 삽입 (복합 PK 처리)
        """
        try:
            total_rows = len(df)
            inserted_count = 0
            error_count = 0
            errors = []
            skipped_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Primary Key 검증: GroupID나 ID가 없으면 건너뛰기
                    if pd.isna(row.get('GroupID')) or pd.isna(row.get('ID')):
                        skipped_count += 1
                        continue
                    
                    # ORM 객체 생성
                    sequence = ProcedureSequence(
                        GroupID=row.get('GroupID'),
                        ID=row.get('ID'),
                        Release=row.get('Release'),
                        Step_Num=row.get('Step_Num'),
                        Element_ID=row.get('Element_ID'),
                        Bundle_ID=row.get('Bundle_ID'),
                        Custom_ID=row.get('Custom_ID'),
                        Sequence_Interval=row.get('Sequence_Interval'),
                        Procedure_Cost=row.get('Procedure_Cost'),
                        Price_Ratio=row.get('Price_Ratio')
                    )
                    
                    # DB에 추가 (복합 PK로 REPLACE 방식)
                    existing = self.db.query(ProcedureSequence).filter(
                        ProcedureSequence.GroupID == row.get('GroupID'),
                        ProcedureSequence.ID == row.get('ID')
                    ).first()
                    
                    if existing:
                        # 기존 레코드 업데이트
                        for key, value in row.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # 새 레코드 추가
                        self.db.add(sequence)
                    
                    inserted_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"행 {index + 1}: {str(e)}")
                    continue
            
            # 커밋
            self.db.commit()
            
            print(f"DEBUG: Procedure_Sequence 삽입 완료 - 총 {total_rows}개, 삽입 {inserted_count}개, 건너뜀 {skipped_count}개, 오류 {error_count}개")
            
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
