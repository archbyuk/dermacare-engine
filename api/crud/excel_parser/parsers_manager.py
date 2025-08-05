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
from ..base import ResultHelper

from .parsers.enum_parser import EnumParser
# from .consumables_parser import ConsumablesParser
# from .global_parser import GlobalParser
# ... 나머지 파서들은 구현되면 추가


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
        
        if 'enum' in filename_lower:
            return EnumParser(self.db)
        # elif 'consumables' in filename_lower:
        #     return ConsumablesParser(self.db)
        # elif 'global' in filename_lower:
        #     return GlobalParser(self.db)
        # elif 'procedure_element' in filename_lower:
        #     return ProcedureElementParser(self.db)
        # elif 'procedure_bundle' in filename_lower:
        #     return ProcedureBundleParser(self.db)
        # elif 'procedure_sequence' in filename_lower:
        #     return ProcedureSequenceParser(self.db)
        # elif 'procedure_info' in filename_lower:
        #     return ProcedureInfoParser(self.db)
        # elif 'procedure_product' in filename_lower:
        #     return ProcedureProductParser(self.db)
        else:
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
            # 1. 파일명으로 적절한 파서 선택
            parser = self.get_parser_by_filename(filename)
            
            # 2. Enum 파일은 독립적으로 처리, 나머지는 공통 파싱 사용
            if parser.table_name == "Enum":
                # Enum은 자체 process_file 메서드 사용 (완전 독립형)
                result = await parser.process_file(file_bytes)
                result['filename'] = filename
                return result
            
            else:
                # 나머지 파일들은 기존 방식 (공통 파싱 + 특화 처리)
                # 2. 엑셀 파싱 (범용 처리) : excel_parser.py 사용
                df = await self.excel_parser.parse_excel(file_bytes)
                
                if df.empty:
                    return self.result_helper.create_error_result(
                        parser.table_name, 
                        "파일이 비어있거나 사용할 데이터가 없습니다"
                    )
                
                # 3. 데이터 검증 (각 파서별 특화 검증)
                is_valid, validation_errors = parser.validate_data(df)
                if not is_valid:
                    return {
                        "success": False,
                        "table_name": parser.table_name,
                        "filename": filename,
                        "errors": validation_errors
                    }
                
                # 4. 데이터 정리 (각 파서별 특화 정리)
                df = parser.clean_data(df)
                
                # 5. DB 삽입 (각 파서별 특화 삽입)
                result = parser.insert_data(df)
                
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