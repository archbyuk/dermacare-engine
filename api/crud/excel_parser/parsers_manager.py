"""
    액셀 파일 파서 관리자: 메인 컨트롤러
        - 파일명에 따른 적절한 파서 선택
        - 전체 워크플로우 관리 (파싱 → 검증 → 정리 → 삽입)
        - API와 각 파서들 사이의 중간 계층
"""

from sqlalchemy.orm import Session
from typing import Dict, Any
from ..excel_parser import ExcelParser
from .abstract_parser import AbstractParser
from .base import ResultHelper

from .parsers.enum_parser import EnumParser
from .parsers.consumables_parser import ConsumablesParser
from .parsers.global_parser import GlobalParser
from .parsers.procedure_element_parser import ProcedureElementParser
from .parsers.procedure_bundle_parser import ProcedureBundleParser
from .parsers.procedure_sequence_parser import ProcedureSequenceParser
from .parsers.procedure_class_parser import ProcedureClassParser
from .parsers.procedure_custom_parser import ProcedureCustomParser
from .parsers.info_standard_parser import InfoStandardParser
from .parsers.info_event_parser import InfoEventParser
from .parsers.info_membership_parser import InfoMembershipParser
from .parsers.product_standard_parser import ProductStandardParser
from .parsers.product_event_parser import ProductEventParser
from .parsers.membership_parser import MembershipParser


class ParsersManager:
    """
        엑셀 파일 처리를 위한 메인 관리자
        파일명에 따라 적절한 파서를 선택하고 전체 워크플로우를 관리
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.excel_parser = ExcelParser()       # 엑셀 파일 범용 파싱 클래스: excel_parser.py
        self.result_helper = ResultHelper()
    
    def get_parser_by_filename(self, filename: str) -> AbstractParser:
        """
            파일명을 기반으로 적절한 파서 선택
            
            Args:
                filename: 업로드된 엑셀 파일명
                
            Returns:
                해당 파일에 맞는 파서 인스턴스 : 
                    enum_parser.py, consumables_parser.py, global_parser.py, procedure_element_parser.py, procedure_bundle_parser.py, procedure_sequence_parser.py, procedure_info_parser.py, procedure_product_parser.py
                
            Raises:
                ValueError: 지원하지 않는 파일명인 경우
        """
        
        filename_lower = filename.lower()
        print(f"DEBUG: 파서 선택 중 - 파일명: {filename}, 소문자: {filename_lower}")
        
        if 'enum' in filename_lower:
            print("DEBUG: EnumParser 선택됨")
            return EnumParser(self.db)
        elif 'consumables' in filename_lower:
            print("DEBUG: ConsumablesParser 선택됨")
            return ConsumablesParser(self.db)
        elif 'global' in filename_lower:
            print("DEBUG: GlobalParser 선택됨")
            return GlobalParser(self.db)
        elif 'procedure_element' in filename_lower:
            print("DEBUG: ProcedureElementParser 선택됨")
            return ProcedureElementParser(self.db)
        elif 'procedure_bundle' in filename_lower:
            print("DEBUG: ProcedureBundleParser 선택됨")
            return ProcedureBundleParser(self.db)
        elif 'procedure_sequence' in filename_lower:
            print("DEBUG: ProcedureSequenceParser 선택됨")
            return ProcedureSequenceParser(self.db)
        elif 'procedure_class' in filename_lower:
            print("DEBUG: ProcedureClassParser 선택됨")
            return ProcedureClassParser(self.db)
        elif 'procedure_custom' in filename_lower:
            print("DEBUG: ProcedureCustomParser 선택됨")
            return ProcedureCustomParser(self.db)
        elif 'info_standard' in filename_lower:
            print("DEBUG: InfoStandardParser 선택됨")
            return InfoStandardParser(self.db)
        elif 'info_event' in filename_lower:
            print("DEBUG: InfoEventParser 선택됨")
            return InfoEventParser(self.db)
        elif 'info_membership' in filename_lower:
            print("DEBUG: InfoMembershipParser 선택됨")
            return InfoMembershipParser(self.db)
        elif 'product_standard' in filename_lower:
            print("DEBUG: ProductStandardParser 선택됨")
            return ProductStandardParser(self.db)
        elif 'product_event' in filename_lower:
            print("DEBUG: ProductEventParser 선택됨")
            return ProductEventParser(self.db)
        elif 'membership' in filename_lower:
            print("DEBUG: MembershipParser 선택됨")
            return MembershipParser(self.db)
        else:
            print(f"DEBUG: 지원하지 않는 파일명: {filename}")
            raise ValueError(f"지원하지 않는 파일명입니다: {filename}")
    
    async def process_excel_file(self, filename: str, file_bytes: bytes) -> Dict[str, Any]:
        """
            엑셀 파일 전체 처리 워크플로우
            
            Args:
                filename: 엑셀 파일명 (파서 선택에 사용)
                file_bytes: 엑셀 파일 바이트 데이터
                
            Returns:
                처리 결과 딕셔너리
        """
        try:
            print(f"DEBUG: process_excel_file 시작 - {filename}")
            
            # 1. 파일명으로 적절한 파서 선택
            parser = self.get_parser_by_filename(filename)
            print(f"DEBUG: 파서 선택 완료 - {parser.table_name}")
            
            # 2. Enum 파일은 독립적으로 처리
            if parser.table_name == "Enum":
                print("DEBUG: Enum 파일 독립 처리")
                # Enum은 자체 process_file 메서드 사용 (완전 독립형)
                result = await parser.process_file(file_bytes)
                result['filename'] = filename
                return result
            
            # 3. 나머지 파일들은 공통 파싱 사용
            print("DEBUG: Excel 파싱 시작")
            df = await self.excel_parser.parse_excel(file_bytes)
            print(f"DEBUG: Excel 파싱 완료 - DataFrame 크기: {df.shape}")
            print(f"DEBUG: DataFrame 컬럼: {df.columns.tolist()}")
            
            if df.empty:
                print("DEBUG: DataFrame이 비어있음")
                return self.result_helper.create_error_result(
                    parser.table_name, 
                    "파일이 비어있거나 사용할 데이터가 없습니다"
                )
            
            # 4. 데이터 검증 (각 파서별 특화 검증)
            print("DEBUG: 데이터 검증 시작")
            is_valid, validation_errors = parser.validate_data(df)
            print(f"DEBUG: 데이터 검증 완료 - 유효성: {is_valid}")
            if not is_valid:
                print(f"DEBUG: 검증 실패 - 오류: {validation_errors}")
                return {
                    "success": False,
                    "table_name": parser.table_name,
                    "filename": filename,
                    "errors": validation_errors
                }
            
            # 5. 데이터 정리 (각 파서별 특화 정리)
            print("DEBUG: 데이터 정리 시작")
            df = parser.clean_data(df)
            print("DEBUG: 데이터 정리 완료")
            
            # 6. DB 삽입 (각 파서별 특화 삽입)
            print("DEBUG: DB 삽입 시작")
            result = parser.insert_data(df)
            print("DEBUG: DB 삽입 완료")
            
            # 파일명 정보 추가
            result['filename'] = filename
            
            return result
            
        except ValueError as e:
            # 지원하지 않는 파일명 등
            return self.result_helper.create_error_result(
                "Unknown",
                f"파일 처리 오류: {str(e)}"
            )
        
        except Exception as e:
            return self.result_helper.create_error_result(
                "Unknown",
                f"파일 처리 중 예상치 못한 오류 발생: {str(e)}"
            )
    
    def get_supported_files(self) -> Dict[str, str]:
        """
        지원하는 파일 목록 반환
        
        Returns:
            {파일명_패턴: 테이블명} 딕셔너리
        """
        return {
            "enum": "Enum",
            "consumables": "Consumables", 
            "global": "Global",
            "procedure_element": "ProcedureElement",
            "procedure_bundle": "ProcedureBundle",
            "procedure_sequence": "ProcedureSequence",
            "procedure_class": "ProcedureClass",
            "info_standard": "InfoStandard",
            "info_event": "InfoEvent",
            "product_standard": "ProductStandard",
            "product_event": "ProductEvent"
        }