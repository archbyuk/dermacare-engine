"""
    ProcedureInfo 테이블 전용 파서
    - 4행 메타데이터 구조 사용 (일반적인 Excel 파싱)
    - 시술 정보: Procedure_ID, Procedure_Name, Procedure_Description, Precautions
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
import pandas as pd
from ..abstract_parser import AbstractParser
from ..base import DataCleaner, ResultHelper
from db.models.procedure_info import ProcedureInfo


class ProcedureInfoParser(AbstractParser):
    """ ProcedureInfo 테이블 전용 파서 클래스 """
    
    def __init__(self, db: Session):
        super().__init__("ProcedureInfo")
        self.db = db
        self.data_cleaner = DataCleaner()
        self.result_helper = ResultHelper()
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        ProcedureInfo 테이블 특화 데이터 검증
        - 필수 컬럼: Procedure_ID, Procedure_Name
        - 선택 컬럼: Procedure_Description, Precautions
        """
        errors = []
        
        # 1. 필수 컬럼 존재 확인
        required_columns = ['Procedure_ID', 'Procedure_Name']
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
        
        # 3. Procedure_ID 숫자 검증
        if 'Procedure_ID' in df.columns:
            non_null_values = df['Procedure_ID'].dropna()
            if not non_null_values.empty:
                try:
                    pd.to_numeric(non_null_values, errors='raise')
                except:
                    errors.append("Procedure_ID 컬럼에 숫자가 아닌 값이 있습니다")
        
        # 4. Procedure_ID 중복 검사 (유효한 데이터가 있을 때만)
        if 'Procedure_ID' in df.columns:
            valid_ids = df['Procedure_ID'].dropna()
            if not valid_ids.empty:
                # 유효한 ID들에 대해서만 중복 검사
                valid_df = df[df['Procedure_ID'].notna()]
                if not valid_df.empty:
                    duplicates = valid_df[valid_df['Procedure_ID'].duplicated(keep=False)]['Procedure_ID'].tolist()
                    if duplicates:
                        errors.append(f"Procedure_ID에 중복된 값이 있습니다: {list(set(duplicates))}")
        
        # 5. 데이터 길이 검증
        if 'Procedure_Name' in df.columns:
            long_names = df[df['Procedure_Name'].astype(str).str.len() > 255].index.tolist()
            if long_names:
                errors.append(f"Procedure_Name이 255자를 초과하는 행들: {[i+1 for i in long_names[:3]]}")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ProcedureInfo 테이블 특화 데이터 정리
        """
        # 1. 공통 정리 작업
        df = self.data_cleaner.clean_common_data(df)
        
        # 2. 문자열 컬럼 정리
        string_columns = ['Procedure_Name', 'Procedure_Description', 'Precautions']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace(['nan', ''], None)
        
        # 3. 정수 컬럼 정리
        if 'Procedure_ID' in df.columns:
            df['Procedure_ID'] = pd.to_numeric(df['Procedure_ID'], errors='coerce').astype('Int64')
        
        # 4. 필수 컬럼이 비어있는 행 제거
        required_columns = ['Procedure_ID', 'Procedure_Name']
        df = df.dropna(subset=required_columns).reset_index(drop=True)
        
        # 5. Procedure_ID 중복 제거 (첫 번째 것만 유지)
        df = df.drop_duplicates(subset=['Procedure_ID'], keep='first').reset_index(drop=True)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ProcedureInfo 테이블에 데이터 삽입
        """
        total_rows = len(df)
        inserted_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        
        # 유효한 데이터가 없으면 성공으로 처리
        if total_rows == 0:
            return self.result_helper.create_success_result(
                table_name="ProcedureInfo",
                total_rows=0,
                inserted_count=0,
                error_count=0,
                errors=[]
            )
        
        try:
            for index, row in df.iterrows():
                try:
                    # Procedure_ID로 기존 데이터 확인 (고유 키)
                    procedure_id = int(row['Procedure_ID'])
                    procedure_name = str(row['Procedure_Name']).strip()
                    
                    if not procedure_name or procedure_name == 'nan':
                        continue  # 빈 Procedure_Name은 건너뛰기
                    
                    existing = self.db.query(ProcedureInfo).filter(
                        ProcedureInfo.Procedure_ID == procedure_id
                    ).first()
                    
                    # 데이터 준비
                    data = {
                        'Procedure_ID': procedure_id,
                        'Procedure_Name': procedure_name,
                        'Procedure_Description': str(row['Procedure_Description']).strip() if pd.notna(row.get('Procedure_Description')) and str(row['Procedure_Description']).strip() != 'None' else None,
                        'Precautions': str(row['Precautions']).strip() if pd.notna(row.get('Precautions')) and str(row['Precautions']).strip() != 'None' else None
                    }
                    
                    if existing:
                        # 기존 데이터 업데이트
                        updated = False
                        for key, value in data.items():
                            if key != 'Procedure_ID':  # 키 필드는 제외
                                if getattr(existing, key) != value:
                                    setattr(existing, key, value)
                                    updated = True
                        
                        if updated:
                            updated_count += 1
                        inserted_count += 1
                    
                    else:
                        # 새로운 데이터 삽입
                        procedure_info = ProcedureInfo(**data)
                        self.db.add(procedure_info)
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
