"""
    [ 데이터 정리 관련 유틸리티 ]
        모든 파서에서 사용할 수 있는 공통 기능 제공

       Where to use > parsers/ *.py > clean_data 함수
"""

import pandas as pd

# [ 데이터 정리 함수 ] : 결측치 처리, 데이터 타입 변환, 공백 제거
def normalize_data(used_df: pd.DataFrame) -> pd.DataFrame:

    # 결측값이 아닌 곳은 True, 결측값(NaN, <NA>, NaT)은 False로 None으로 바꾸는 작업
    # AND -1, ''(빈 값), 특수하게 들어올 수 있는 NaN 값을 None으로 바꾸는 작업
    used_df = used_df.where(
        pd.notnull(used_df), None
    ).replace(
        [
            -1, '-1', 
            '', ' ', '\t', '\n', '\r', 
            'nan','NaN', 'Nan', 'NAN',
            'none' ,'None','<None>', 
            'null', 'Null', 'NULL', '<null>', '<Null>', '<NULL>',
            'na', 'NA', '<NA>', '<na>', float('nan'),
            'N/A','n/a', 'n/A', '<N/A>', '<n/a>', '<n/A>',
            'NaT', 'nat', '<Nat>', '<nat>', '<NaT>', '<nat>'
        ], None
    )

    # 숫자 타입 데이터: Int, Float 타입을 object로 변환 >> sqlalchemy 호환성 위해
    num_columns = used_df.select_dtypes(
        include=['number']
    ).columns
    
    used_df[num_columns] = used_df[num_columns].astype(object)

    # 모든 컬럼의 데이터 타입을 object로 변환
    for column in used_df.columns:
        
        # 문자열 데이터의 앞뒤 공백 제거: None이 아닌 데이터만 처리
        used_df[column] = used_df[column].apply(
            lambda object_data: str(object_data).strip() 
                if pd.notna(object_data) 
                else object_data
        )


    # 정리된 데이터프레임 반환: 모든 컬럼의 데이터 타입을 object로 변환 후 row data의 앞뒤 공백 제거
    return used_df