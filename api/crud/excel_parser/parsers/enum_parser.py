"""
    Enum 테이블 전용 파서
    - 특별한 구조: ID, ClassMajor, ClassSub, ClassDetail 등 여러 분류 체계
    - 4행 메타데이터 구조 사용 안함 (일반 엑셀 테이블 구조)
    - 자체 파싱부터 삽입까지 모든 기능 포함
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
import pandas as pd
import io
from ..abstract_parser import AbstractParser
from ..base import DataCleaner, ResultHelper
from db.models.enum import Enum


class EnumParser(AbstractParser):
    """ Enum 테이블 전용 파서 클래스 - 완전 독립형 """
    
    def __init__(self, db: Session):
        super().__init__("Enum")
        self.db = db
        self.data_cleaner = DataCleaner()
        self.result_helper = ResultHelper()
    
    async def parse_excel(self, file_bytes: bytes) -> pd.DataFrame:
        """
            Enum 전용 엑셀 파싱
            - 일반적인 엑셀 테이블 구조 (4행 메타데이터 구조 안 씀)
            - ID, ClassMajor, ClassSub, ClassDetail 등의 컬럼 구조
        """
        try:
            # 일반적인 엑셀 파일 읽기 (첫 번째 행이 헤더)
            df = pd.read_excel(io.BytesIO(file_bytes), header=0)
            
            # 빈 행 제거
            df = df.dropna(how='all').reset_index(drop=True)
            
            if df.empty:
                raise Exception("엑셀 파일이 비어있습니다")
            
            # 컬럼명 정리 (공백 제거)
            df.columns = df.columns.str.strip()
            
            return df
            
        except Exception as e:
            raise Exception(f"Enum 엑셀 파일 파싱 실패: {str(e)}")
    
    async def process_file(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Enum 파일 전체 처리 워크플로우 (독립적)
        1. 자체 파싱
        2. 검증
        3. 정리
        4. 삽입
        """
        try:
            # 1. Enum 전용 파싱
            df = await self.parse_excel(file_bytes)
            
            if df.empty:
                return self.result_helper.create_error_result(
                    self.table_name,
                    "파일이 비어있거나 사용할 데이터가 없습니다"
                )
            
            # 2. 데이터 검증
            is_valid, validation_errors = self.validate_data(df)
            if not is_valid:
                return {
                    "success": False,
                    "table_name": self.table_name,
                    "errors": validation_errors
                }
            
            # 3. 데이터 정리
            df = self.clean_data(df)
            
            # 4. DB 삽입
            result = self.insert_data(df)
            
            return result
            
        except Exception as e:
            return self.result_helper.create_error_result(
                self.table_name,
                f"파일 처리 중 오류 발생: {str(e)}"
            )
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Enum 테이블 특화 데이터 검증
        - 실제 Enum 구조에 맞는 검증: ID, ClassMajor, ClassSub 등
        """
        errors = []
        
        # 1. 기본 컬럼 존재 확인 (최소한 ID 컬럼은 있어야 함)
        if 'ID' not in df.columns:
            errors.append("ID 컬럼이 없습니다")
            return False, errors
        
        # 2. 분류 컬럼들 중 하나라도 있는지 확인
        classification_columns = ['ClassMajor', 'ClassSub', 'ClassDetail', 'ClassType', 
                                'PositionType', 'UnitType', 'PackageType']
        
        existing_class_columns = [col for col in classification_columns if col in df.columns]
        if not existing_class_columns:
            errors.append(f"분류 컬럼이 없습니다. 다음 중 하나는 있어야 합니다: {classification_columns}")
        
        # 3. ID 중복 검사 (각 분류별로)
        for col in existing_class_columns:
            # 해당 분류에서 ID 중복 체크
            col_data = df[['ID', col]].dropna()
            if not col_data.empty:
                duplicates = col_data[col_data.duplicated(subset=['ID'], keep=False)]
                if not duplicates.empty:
                    duplicate_ids = duplicates['ID'].unique().tolist()
                    errors.append(f"{col} 분류에서 중복된 ID: {duplicate_ids}")
        
        # 4. 데이터 길이 검증 (각 분류명이 너무 길지 않은지)
        for col in existing_class_columns:
            if col in df.columns:
                long_values = df[col].dropna().astype(str)
                long_values = long_values[long_values.str.len() > 100]  # 100자 제한
                if not long_values.empty:
                    errors.append(f"{col} 컬럼에 100자를 초과하는 값이 있습니다")
        
        # 5. ID가 숫자인지 확인
        try:
            pd.to_numeric(df['ID'].dropna(), errors='raise')
        except:
            errors.append("ID 컬럼에 숫자가 아닌 값이 있습니다")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enum 테이블 특화 데이터 정리
        - ID, ClassMajor, ClassSub 등 실제 구조에 맞는 정리
        """
        # 1. 공통 정리 작업 실행
        df = self.data_cleaner.clean_common_data(df)
        
        # 2. ID 컬럼 정리 (숫자로 변환)
        if 'ID' in df.columns:
            df['ID'] = pd.to_numeric(df['ID'], errors='coerce').astype('Int64')
        
        # 3. 분류 컬럼들 정리
        classification_columns = ['ClassMajor', 'ClassSub', 'ClassDetail', 'ClassType', 
                                'PositionType', 'UnitType', 'PackageType']
        
        for col in classification_columns:
            if col in df.columns:
                # 문자열로 변환하고 공백 제거
                df[col] = df[col].astype(str).str.strip()
                
                # 'nan', 빈 문자열을 None으로 변환
                df[col] = df[col].replace(['nan', ''], None)
                
                # None이 아닌 경우만 문자열 처리
                df[col] = df[col].apply(lambda x: x if x is None else str(x).strip())
        
        # 4. 빈 행 제거 (모든 분류 컬럼이 None인 행)
        classification_cols_in_df = [col for col in classification_columns if col in df.columns]
        if classification_cols_in_df:
            # 모든 분류 컬럼이 None인 행 제거
            df = df.dropna(subset=classification_cols_in_df, how='all').reset_index(drop=True)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
            Enum 테이블에 데이터 삽입
            - 실제 Enum 구조: ID + 여러 분류 컬럼들
            - 각 분류별로 별도 처리 (ID-분류값 쌍으로)
        """
        total_rows = 0
        inserted_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        
        # 분류 컬럼들 확인
        classification_columns = ['ClassMajor', 'ClassSub', 'ClassDetail', 'ClassType', 
                                'PositionType', 'UnitType', 'PackageType']
        existing_class_columns = [col for col in classification_columns if col in df.columns]
        
        try:
            # 각 분류 컬럼별로 처리
            for class_col in existing_class_columns:
                # 해당 분류의 데이터만 추출 (ID와 분류값이 모두 있는 행만)
                class_data = df[['ID', class_col]].dropna()
                
                for index, row in class_data.iterrows():
                    total_rows += 1
                    
                    try:
                        id_val = int(row['ID'])
                        class_val = str(row[class_col]).strip()
                        
                        if not class_val or class_val == 'None':
                            continue  # 빈 값은 건너뛰기
                        
                        # 기존 데이터 확인 (ID와 분류 타입으로)
                        existing = self.db.query(Enum).filter(
                            Enum.ID == id_val,
                            Enum.Type == class_col  # Type 필드에 분류 타입 저장
                        ).first()
                        
                        if existing:
                            # 기존 데이터 업데이트
                            if existing.Code != class_val:
                                existing.Code = class_val
                                updated_count += 1
                            inserted_count += 1
                        else:
                            # 새로운 데이터 삽입
                            enum_item = Enum(
                                ID=id_val,
                                Type=class_col,      # 분류 타입 (ClassMajor, ClassSub 등)
                                Code=class_val,      # 실제 분류값 (레이저, 인젠 등)
                                Name=None            # 현재 구조에서는 Name 없음
                            )
                            self.db.add(enum_item)
                            inserted_count += 1
                        
                        # 매 50개마다 커밋 (성능 최적화)
                        if total_rows % 50 == 0:
                            self.db.commit()
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {index + 1}, {class_col}: {str(e)}")
                        self.db.rollback()
            
            # 최종 커밋
            self.db.commit()
            
        except Exception as e:
            error_count += total_rows  # 전체 실패로 처리
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
        result['processed_classifications'] = existing_class_columns
        
        return result
