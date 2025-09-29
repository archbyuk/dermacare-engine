"""
    [ 데이터프레임 변환 유틸리티 ]
        다운로드 한 액셀 파일을 데이터프레임(pandas dataframe)으로 변환하는 유틸리티

    [ 변환할 파일 데이터 ]
        - file_data: 다운로드 한 액셀 파일 데이터(bytes형태)
"""

import pandas as pd
import io

class DataFrameUtils:

    # 다운로드 받은 파일을 데이터프레임으로 변환 후 반환. 반환과정에서 사용하지 않을 행은 제외
    
    # [ Enum 파일 제외한 나머지 파일 ]
    def remain_dataframe_utils(
        self,
        file_data: bytes    # 다운로드 받은 파일 데이터 (bytes형태)
    ) -> pd.DataFrame:

        try:
            # 1. file_data라는 bytes 형태의 데이터를 읽어와 데이터프레임으로 변환
            raw_df = pd.read_excel(
                io.BytesIO(file_data),
                header=None
            ).dropna(how='all')     # 데이터프레임에서 빈 행 제거


            # 2. 데이터프레임에 충분한 행이 있는 지 확인
            if len(raw_df) < 5:
                raise Exception("엑셀 파일에 충분한 데이터가 없습니다 (최소 5행 필요)")

            # 2-1. 변환된 데이터프레임에서 1~4행까지의 메타 데이터 추출
            column_enable = raw_df.iloc[1].fillna(0)         # 2행: 사용 여부
            column_types = raw_df.iloc[2].fillna('')         # 3행: 자료형
            column_names = raw_df.iloc[3].fillna('')         # 4행: DB 컬럼명

            # 2-2. 사용할 컬럼 인덱스 찾기 
            # 2행, column_enable이 숫자 1인 컬럼들의 인덱스 번호를 리스트로 반환
            selected_columns = column_enable[column_enable == 1].index.tolist()

            if not selected_columns:
                raise Exception("사용할 컬럼이 없습니다 (2행에 1로 표시된 컬럼이 없음)")


            # 3. 5행부터 사용할 컬럼들(selected_columns [type: list(int)] )만 추출 후 index 다시 0부터 시작
            used_df = raw_df.iloc[4:, selected_columns].reset_index(drop=True)

            # 3-1. 컬럼명 설정: 사용할 컬럼들의 인덱스 번호를 column_names 리스트에서 찾아 컬럼명 설정
            used_df.columns = [column_names[i] for i in selected_columns]

            # 3-2. used_df에서 빈 행 제거
            used_df = used_df.dropna(how='all').reset_index(drop=True)

            # 4. used_df에서 데이터 타입 변환
            for i, column in enumerate(selected_columns):
                if i >= len(used_df.columns):
                    continue
                
                # column_name: 컬럼명
                column_name = used_df.columns[i]
                
                # column_type: 컬럼 타입
                column_type = column_types[column].upper().strip() if column < len(column_types) else ''
                
                
                if 'INT' in column_type:
                    
                    if column_name == 'VAT':
                        numeric_data = pd.to_numeric(used_df[column_name], errors='coerce')
                        used_df[column_name] = numeric_data.round().astype('Int64')

                        continue
                    
                    used_df[column_name] = pd.to_numeric(used_df[column_name], errors='coerce').astype('Int64')
                
                elif 'FLOAT' in column_type or 'DECIMAL' in column_type:
                    if column_name == 'F_Value':
                        numeric_data = pd.to_numeric(used_df[column_name], errors='coerce')
                        used_df[column_name] = numeric_data.astype('float64')
                        
                        continue
                    
                    used_df[column_name] = pd.to_numeric(used_df[column_name], errors='coerce')
                
                elif 'BOOL' in column_type:
                    used_df[column_name] = pd.to_numeric(used_df[column_name], errors='coerce').astype('Int64')
                
                elif 'VARCHAR' in column_type or 'TEXT' in column_type or 'STRING' in column_type:
                    used_df[column_name] = used_df[column_name].astype(str).replace('nan', None)

                
            
            # 5. Release 필터링 (Release 컬럼이 있는 경우)
            if 'Release' in used_df.columns:
                release_columns = used_df['Release']
                used_df = used_df[release_columns.isin([0, 1])].copy().reset_index(drop=True)

            # 데이터프레임 반환
            return used_df

        except Exception as e:
            raise Exception(f"데이터프레임 변환 중 오류 발생: {str(e)}")


    # [ Enum 파일 ]
    def enum_dataframe_utils(
        self,
        file_data: bytes    # 다운로드 받은 파일 데이터 (bytes형태)
    ) -> pd.DataFrame:
    
        try:
            # 1. file_data라는 bytes 형태의 데이터를 읽어와 데이터프레임으로 변환
            raw_df = pd.read_excel(
                io.BytesIO(file_data), 
                header=None
            ).dropna(how='all')     # 데이터프레임에서 빈 행 제거

            
            # 2. 데이터프레임에 충분한 행이 있는 지 확인: Enum 파일은 최소 2행 필요
            if len(raw_df) < 2:
                raise Exception("Enum 파일에 충분한 데이터가 없습니다")
            
            # 첫 번째 행 전처리: 빈 값은 빈 문자열로 채우고 가져온 컬럼을 전부 문자열로 변환 후 공백 제거(지운 거 아님)
            all_columns= raw_df.iloc[0].fillna('').astype(str).str.strip()
            
            # 유효한 컬럼 필터링: AND 조건으로 빈값 제외, ID 컬럼 제외
            enum_types = (
                all_columns != ''
            ) & (
                ~all_columns.str.startswith('ID')
                )

            # ex) enum_types: [false, false, true...]
            
            # any(): 조건에 만족하는 값이 하나라도 있는지 확인: not '' and not 'ID'
            if not enum_types.any():
                raise Exception("유효한 Enum 컬럼이 없습니다")

            # 2-1. 유효한 컬럼들의 실제 데이터만 추출 (1행부터 끝까지, columns_mask에 해당하는 컬럼들만 추출)

            # valid_data는 DataFrame (유효한 컬럼들의 데이터)
            # valid_data = raw_df.iloc[1:, enum_types]
            valid_columns_indices = enum_types[enum_types].index.tolist()
            valid_data = raw_df.iloc[1:, valid_columns_indices]

            # valid_columns는 리스트 (유효한 컬럼명들)
            valid_columns = all_columns[enum_types]
            
            # 데이터 수집을 위한 딕셔너리 (메모리 효율성): enum_type, id, name(이게 DB에 들어갈 컬럼명)
            enum_dict = {
                'enum_type': [],
                'id': [],
                'name': []
            }
            
            # 틈새 문법: iloc[x, y] -> x: 행, y: 열 > 원하는 행과 열을 선택하는 메서드

            # 각 유효한 컬럼 처리 (
            #   valid_columns [type: list(str):'Position_Type', 'Procedure_Level', 'Payment_Method']
            # )
            for idx, enum_type in enumerate(valid_columns):
                
                # 해당 컬럼의 데이터 추출 및 정리(valid_data [type: pd.DataFrame]: 유효한 컬럼들의 실제 데이터)
                column_data = valid_data.iloc[:, idx].dropna()
                # idx열에 해당되는 모든 행의 데이터를 뽑아내는 부분

                # DB에 들어갈 name 생성: 데이터 중 빈 값이 아닌 데이터만 처리, 그리고 전부 문자열로 변환
                used_names = (
                    column_data.dropna()
                    .astype(str)
                    .str.strip()
                    .loc[lambda name: name != ""]
                )

                
                # used_data가 비어있으면 다음 컬럼으로 넘어감
                if len(used_names) == 0:
                    continue
                
                # DB에 들어갈 ID 생성: used_names 길이(즉, 행의 개수)만큼 10씩 증가하는 리스트 생성
                used_ids = [
                    (id_idx + 1) * 10 for id_idx in range(len(used_names))
                ]
                
                # 딕셔너리에 데이터 추가
                enum_dict['enum_type'].extend(
                    [enum_type] * len(used_names)
                ) # 하나의 enum_type에 대해 여러 개의 name이 있을 수 있으므로 반복
                enum_dict['id'].extend(used_ids)
                enum_dict['name'].extend(used_names.tolist())
            
            # enum_dict['enum_type']가 비어있으면 오류 발생
            if not enum_dict['enum_type']:
                raise Exception("추출할 Enum 데이터가 없습니다")
            
            # DataFrame으로 변환
            used_df = pd.DataFrame(enum_dict)

            print("[DEBUG] Enum 데이터프레임 변환 완료: ", used_df)
            
            return used_df
            
        except Exception as e:
            raise Exception(f"Enum 데이터프레임 변환 중 오류 발생: {str(e)}")