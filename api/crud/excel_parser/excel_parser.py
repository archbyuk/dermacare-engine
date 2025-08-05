"""
    순수 엑셀 파싱 전용 클래스
    메타데이터 기반 엑셀 파일을 DataFrame으로 변환하는 것만 담당
"""

import pandas as pd
import io
from typing import Dict, Any, List


class ExcelParser:
    """ 엑셀 파일을 DataFrame으로 변환하는 순수 파싱 클래스 """
    
    async def parse_excel(self, file_bytes: bytes) -> pd.DataFrame:
        """
            엑셀 파일을 DataFrame으로 파싱 (메타데이터 구조 처리)
            
            엑셀 구조:
                1행: 컬럼 설명
                2행: 사용 여부 (1=사용, 0=미사용)
                3행: 자료형 (INT, VARCHAR, BOOLEAN 등)
                4행: 실제 컬럼명 (DB 컬럼명)
                5행부터: 실제 데이터
        """
        try:
            # BytesIO로 메모리에서 파일 처리
            raw_df = pd.read_excel(io.BytesIO(file_bytes), header=None)
            
            # 빈 행 제거
            raw_df = raw_df.dropna(how='all')
            
            # 최소 5행은 있어야 함 (메타데이터 4행 + 데이터 1행)
            if len(raw_df) < 5:
                raise Exception("엑셀 파일에 충분한 데이터가 없습니다 (최소 5행 필요)")
            
            # 메타데이터 추출
            metadata = self.extract_metadata(raw_df)
            
            # 실제 데이터만 추출 (5행부터)
            data_df = raw_df.iloc[4:].reset_index(drop=True)
            
            # 사용할 컬럼만 선택하고 컬럼명 설정
            processed_df = self.process_with_metadata(data_df, metadata)
            
            return processed_df
            
        except Exception as e:
            raise Exception(f"엑셀 파일 파싱 실패: {str(e)}")
    
    def extract_metadata(self, raw_df: pd.DataFrame) -> Dict[str, Any]:
        """
            엑셀 파일에서 메타데이터 추출
            
            Returns:
                Dict containing:
                - descriptions: 컬럼 설명 (1행)
                - use_flags: 사용 여부 (2행)
                - data_types: 자료형 (3행)
                - column_names: 컬럼명 (4행)
                - selected_columns: 사용할 컬럼 인덱스 리스트
        """
        try:
            # 각 행에서 메타데이터 추출
            descriptions = raw_df.iloc[0].fillna('').tolist()
            use_flags = raw_df.iloc[1].fillna(0).tolist()
            data_types = raw_df.iloc[2].fillna('').tolist()
            column_names = raw_df.iloc[3].fillna('').tolist()
            
            # 사용할 컬럼 인덱스 찾기 (2행이 1인 컬럼들)
            selected_columns = []
            for i, flag in enumerate(use_flags):
                try:
                    # 1 또는 '1'인 경우 선택
                    if str(flag).strip() == '1' or flag == 1:
                        selected_columns.append(i)
                except:
                    continue
            
            if not selected_columns:
                raise Exception("사용할 컬럼이 없습니다 (2행에 1로 표시된 컬럼이 없음)")
            
            return {
                'descriptions': descriptions,
                'use_flags': use_flags,
                'data_types': data_types,
                'column_names': column_names,
                'selected_columns': selected_columns
            }
            
        except Exception as e:
            raise Exception(f"메타데이터 추출 실패: {str(e)}")
    
    def process_with_metadata(self, data_df: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """
            메타데이터를 기반으로 데이터 처리
            
            1. 사용할 컬럼만 선택
            2. 컬럼명 설정
            3. 데이터 타입 변환
        """
        try:
            selected_columns = metadata['selected_columns']
            column_names = metadata['column_names']
            data_types = metadata['data_types']
            
            # 사용할 컬럼만 선택
            selected_df = data_df.iloc[:, selected_columns].copy()
            
            # 컬럼명 설정
            new_column_names = [column_names[i] for i in selected_columns]
            selected_df.columns = new_column_names
            
            # 빈 행 제거
            selected_df = selected_df.dropna(how='all').reset_index(drop=True)
            
            # 데이터 타입 변환
            selected_df = self.convert_data_types(selected_df, selected_columns, data_types)
            
            return selected_df
            
        except Exception as e:
            raise Exception(f"메타데이터 기반 처리 실패: {str(e)}")
    
    def convert_data_types(self, df: pd.DataFrame, selected_columns: List[int], data_types: List[str]) -> pd.DataFrame:
        """
            3행의 자료형 정보를 기반으로 데이터 타입 변환
        """
        try:
            for i, col_idx in enumerate(selected_columns):
                if i >= len(df.columns):
                    continue
                    
                col_name = df.columns[i]
                data_type = data_types[col_idx].upper().strip() if col_idx < len(data_types) else ''
                
                # 데이터 타입별 변환
                if 'INT' in data_type:
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Int64')
                elif 'FLOAT' in data_type or 'DECIMAL' in data_type:
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                elif 'BOOL' in data_type:
                    df[col_name] = df[col_name].astype('boolean')
                elif 'VARCHAR' in data_type or 'TEXT' in data_type or 'STRING' in data_type:
                    df[col_name] = df[col_name].astype(str)
                    # 'nan' 문자열을 None으로 변환
                    df[col_name] = df[col_name].replace('nan', None)
                
            return df
            
        except Exception as e:
            # 타입 변환 실패해도 원본 데이터는 유지
            print(f"데이터 타입 변환 중 오류 (무시하고 계속): {str(e)}")
            return df