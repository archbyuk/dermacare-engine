"""
    [ 파일 파싱 서비스 ] (기존 parser_manager.py 리팩토링)
    
    파일 파싱 관련 공통 로직 및 유틸리티
"""
from sqlalchemy.orm import Session    
from fastapi import HTTPException
from typing import Dict, Any, List
import asyncio

# 유틸리티 클래스 import
from ..utils.dataframe_utils import DataFrameUtils
from ..utils.abstract_utils import AbstractUtils

# 파서 클래스 import
from ..parsers.enum_parser import EnumParser
from ..parsers.consumables_parser import ConsumablesParser
from ..parsers.global_parser import GlobalParser
from ..parsers.info_event_parser import InfoEventParser
from ..parsers.info_standard_parser import InfoStandardParser
from ..parsers.info_membership_parser import InfoMembershipParser
from ..parsers.procedure_class_parser import ProcedureClassParser
from ..parsers.procedure_element_parser import ProcedureElementParser
from ..parsers.procedure_bundle_parser import ProcedureBundleParser
from ..parsers.procedure_custom_parser import ProcedureCustomParser
from ..parsers.procedure_sequence_parser import ProcedureSequenceParser
from ..parsers.product_standard_parser import ProductStandardParser
from ..parsers.product_event_parser import ProductEventParser
from ..parsers.membership_parser import MembershipParser


class ParserService:

    # constructor: db 초기화 (클래스 내부에서 사용할 db 세션 초기화)
    def __init__(self, db: Session):
        self.db = db
        self.dataframe_utils = DataFrameUtils()
        

    # 파일명을 기반으로 적절한 파서 선택
    # AbstractUtils를 반환하는 이유는 파서 클래스들이 AbstractUtils를 상속받기 때문이고 parsing_process에서 직접 호출할 거여서
    def mapping_parser(self, filename: str) -> AbstractUtils:
        
        try:
            filename_lower = filename.lower()

            if 'enum' in filename_lower:
                return EnumParser(self.db)

            elif 'global' in filename_lower:
                return GlobalParser(self.db)

            elif 'consumables' in filename_lower:
                return ConsumablesParser(self.db)

            elif 'procedure_class' in filename_lower:
                return ProcedureClassParser(self.db)

            elif 'procedure_element' in filename_lower:
                return ProcedureElementParser(self.db)

            elif 'procedure_bundle' in filename_lower:
                return ProcedureBundleParser(self.db)

            elif 'procedure_custom' in filename_lower:
                return ProcedureCustomParser(self.db)

            elif 'procedure_sequence' in filename_lower:
                return ProcedureSequenceParser(self.db)

            elif 'info_standard' in filename_lower:
                return InfoStandardParser(self.db)

            elif 'info_event' in filename_lower:
                return InfoEventParser(self.db)

            elif 'info_membership' in filename_lower:
                return InfoMembershipParser(self.db)

            elif 'product_standard' in filename_lower:
                return ProductStandardParser(self.db)

            elif 'product_event' in filename_lower:
                return ProductEventParser(self.db)

            elif 'membership' in filename_lower:
                return MembershipParser(self.db)
            
            else:
                raise ValueError(f"지원하지 않는 파일명입니다: {filename}")

        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"파일 파싱 중 오류 발생: {str(e)}"
            )
    
    # mapping_parser 함수를 이용하여 파일명을 기반으로 파서를 선택한 후 파싱 처리 로직
    async def parsing_process(self, filename: str, file_data: bytes):
        """
            params:
                - filename: 파일명
                - file_data: 파일 데이터 (bytes 형태로 다운로드 된 파일 데이터)
        """
        
        try:
            # 파일명을 기반으로 파서를 선택 (mapping_parser 함수 사용)
            selected_parser = self.mapping_parser(filename)

            # ==== 테이블 분기 처리 후 추상 메서드로 정의된 공통 함수 로직 ==== #
            
            # Enum 테이블은 행열 구조가 특이하므로 별도 처리
            if selected_parser.table_name == "Enum":
                used_df = self.dataframe_utils.enum_dataframe_utils(file_data)
        
            # 나머지 테이블은 행열 구조가 동일하므로 공통 로직 사용
            else:
                used_df = self.dataframe_utils.remain_dataframe_utils(file_data)

            # 데이터프레임이 비어있으면 오류 발생 (모든 테이블 공통 검증)
            if used_df.empty:
                return {
                    "success": False,
                    "table_name": selected_parser.table_name,
                    "error": "파일이 비어있거나 사용할 데이터가 없습니다",
                }

            # 데이터프레임 검증 (abstract_utils을 상속받는 파서의 validate_data 함수 사용)
            # 반환 타입: Tuple[bool, List[str]] > unpacking해서 나눠 받기
            is_valid, validation_errors = selected_parser.validate_data(used_df, filename)
            
            # 검증 실패 시 오류 발생
            if not is_valid:
                print(f"DEBUG: 검증 실패 - 오류: {validation_errors}")
                
                return {
                    "success": False,
                    "table_name": selected_parser.table_name,
                    "filename": filename,
                    "errors": validation_errors
                }
            
            # 5. 데이터 정리 (각 파서별 특화 정리)부터 시작: nomalized_data 함수 사용
            # abstract_utils의 clean_data 함수 사용 (자동 상속)

            print("[DEBUG] 데이터 정리 시작: ", used_df)
            used_df = selected_parser.clean_data(used_df)

            print("[DEBUG] 데이터 정리 완료: ", used_df)

            # 6. DB 삽입 (각 파서별 특화 삽입): 일요일에 오면 여기부터 시작 insert_data 함수 사용
            result_df = selected_parser.insert_data(used_df)
            
            # 기존 result_df에 파일명 추가
            # 추가 시:
            #   {
            #      "success": True,
            #      "table_name": "Enum",
            #      "total_rows": 10,
            #      "inserted_count": 10,
            #      "error_count": 0,
            #      "errors": None,
            #      "filename": "{filename}.xlsx"
            #   }
            result_df['filename'] = filename

            return result_df


        except Exception as e:
            # ValueError 예외 처리
            if isinstance(e, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"지원하지 않는 파일명입니다: {filename}"
                )
            
            # 그 외 예외 처리
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"파일 파싱 중 오류 발생: {str(e)}"
                )
    
    # 파일 다운로드 후 파싱 처리 로직(asyncio로 일괄 처리 사용)
    async def parser_process(
        self,
        download_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        try:
            # 각 파일별로 파싱 작업 지정 후 작업 목록 생성
            parse_tasks = []

            # 파싱 중 에러 발생 시 에러 결과 저장
            error_results = []
            
            print("[DEBUG] 파싱 작업 목록 생성 시작: ", parse_tasks)

            for download_info in download_results:
                task = asyncio.create_task(
                    self.parsing_process(
                        download_info['file_name'],
                        download_info['file_data']
                    )
                )
                
                parse_tasks.append(task)

            # 매핑한 모든 파싱 작업 동시 실행
            parsered_results = await asyncio.gather(*parse_tasks)

            print(f"DEBUG: 파싱 결과: {parsered_results}")

            # 파싱 중 에러 발생 시 에러 결과 저장
            for parsered_result in parsered_results:
                if not parsered_result.get("success", False):
                    error_results.append(
                        {
                            'filename': parsered_result.get('filename'),
                            'table_name': parsered_result.get('table_name'),
                            'error': parsered_result.get('error')
                        }
                    )

            # 파싱 결과 반환
            return parsered_results, error_results

        
        except Exception as e:
            # ValueError 예외 처리
            if isinstance(e, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"지원하지 않는 파일명입니다: {download_info['file_name']}"
                )
            
            # 그 외 예외 처리
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"파일 파싱 중 오류 발생: {str(e)}"
                )