"""
Enum 테이블용 Excel 파서
열거형 데이터를 Excel에서 읽어 DB에 삽입 (복합 PK: enum_type, id)
특별한 구조: 각 열이 다른 enum_type, 행이 id와 name을 나타냄
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
import io

from ..abstract_parser import AbstractParser
from db.models.enum import Enum


class EnumParser(AbstractParser):
    """열거형 테이블 파서 - 특별한 Excel 구조 처리"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session, "Enum")
    
    async def process_file(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Enum 파일은 특별한 구조이므로 독립적으로 처리
        각 열이 서로 다른 enum_type을 나타내는 구조
        """
        try:
            # BytesIO로 메모리에서 파일 처리
            raw_df = pd.read_excel(io.BytesIO(file_bytes), header=None)
            
            # 빈 행 제거
            raw_df = raw_df.dropna(how='all')
            
            if len(raw_df) < 2:
                return self.result_helper.create_error_result(
                    self.table_name, 
                    "Enum 파일에 충분한 데이터가 없습니다"
                )
            
            # Enum 데이터 추출 및 변환
            enum_data = []
            
            # 첫 번째 행의 각 컬럼이 enum_type
            enum_types = raw_df.iloc[0].fillna('').tolist()
            
            # 각 컬럼 처리
            for col_idx, enum_type in enumerate(enum_types):
                if not enum_type or str(enum_type).strip() == '':
                    continue
                    
                enum_type = str(enum_type).strip()
                
                # "ID"로 시작하는 컬럼들은 실제 enum_type이 아니므로 제외
                if enum_type == 'ID' or enum_type.startswith('ID'):
                    continue
                
                # 해당 컬럼의 데이터 추출 (첫 번째 행 제외)
                column_data = raw_df.iloc[1:, col_idx].dropna()
                
                # ID와 name 분리 (각 enum_type별로 간단한 ID 생성: 10, 20, 30...)
                for row_idx, name_value in enumerate(column_data):
                    if pd.notna(name_value) and str(name_value).strip():
                        # 각 enum_type별로 10, 20, 30... 형태의 간단한 ID 생성
                        enum_id = (row_idx + 1) * 10
                        name = str(name_value).strip()
                        
                        enum_data.append({
                            'enum_type': enum_type,
                            'id': enum_id,
                            'name': name
                        })
            
            if not enum_data:
                return self.result_helper.create_error_result(
                    self.table_name, 
                    "추출할 Enum 데이터가 없습니다"
                )
            
            # DataFrame으로 변환
            df = pd.DataFrame(enum_data)
            
            # 데이터 검증
            is_valid, validation_errors = self.validate_data(df)
            if not is_valid:
                return {
                    "success": False,
                    "table_name": self.table_name,
                    "errors": validation_errors
                }
            
            # 데이터 정리
            df = self.clean_data(df)
            
            # DB 삽입
            result = self.insert_data(df)
            
            return result
            
        except Exception as e:
            return self.result_helper.create_error_result(
                self.table_name,
                f"Enum 파일 처리 중 오류 발생: {str(e)}"
            )
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Enum 데이터 검증"""
        errors = []
        
        # 필수 컬럼 확인
        required_columns = ['enum_type', 'id', 'name']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"필수 컬럼이 없습니다: {col}")
        
        if errors:
            return False, errors
        
        # 복합 PK 중복 확인
        duplicated_mask = df[['enum_type', 'id']].duplicated()
        if duplicated_mask.any():
            duplicated_pairs = df[duplicated_mask][['enum_type', 'id']].values.tolist()
            errors.append(f"중복된 (enum_type, id) 조합이 있습니다: {duplicated_pairs}")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enum 데이터 정리"""
        # 기본 공통 정리
        df = self.data_cleaner.clean_common_data(df)
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Enum 테이블에 데이터 삽입"""
        try:
            total_rows = len(df)
            inserted_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # ORM 객체 생성
                    enum_obj = Enum(
                        enum_type=row.get('enum_type'),
                        id=row.get('id'),
                        name=row.get('name')
                    )
                    
                    # DB에 추가 (복합 PK로 REPLACE 방식)
                    existing = self.db.query(Enum).filter(
                        Enum.enum_type == row.get('enum_type'),
                        Enum.id == row.get('id')
                    ).first()
                    
                    if existing:
                        # 기존 레코드 업데이트
                        existing.name = row.get('name')
                    else:
                        # 새 레코드 추가
                        self.db.add(enum_obj)
                    
                    inserted_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"행 {index + 1}: {str(e)}")
                    continue
            
            # 커밋
            self.db.commit()
            
            return self.result_helper.create_result_dict(
                table_name=self.table_name,
                total_rows=total_rows,
                inserted_count=inserted_count,
                error_count=error_count,
                errors=errors if errors else None
            )
            
        except Exception as e:
            self.db.rollback()
            return self.result_helper.create_error_result(
                table_name=self.table_name,
                error_message=f"삽입 중 오류 발생: {str(e)}"
            )
