"""
    추상 파서 클래스
    각 구체적 파서(EnumParser, ConsumablesParser 등)가 구현해야 하는 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from .base import DataCleaner, ResultHelper


class AbstractParser(ABC):
    """ 모든 파서가 구현해야 하는 추상 클래스 """
    
    def __init__(self, db_session: Session, table_name: str):
        self.db = db_session
        self.table_name = table_name
        self.data_cleaner = DataCleaner()
        self.result_helper = ResultHelper()
    
    @abstractmethod
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
            데이터 검증 로직
            각 파서에서 테이블별 특화 검증 구현
            
            Args:
                df: 검증할 DataFrame
                
            Returns:
                Tuple[bool, List[str]]: (검증 성공 여부, 에러 메시지 리스트)
        """
        pass
    
    @abstractmethod
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
            데이터 정리 로직
            각 파서에서 테이블별 특화 정리 구현
            
            Args:
                df: 정리할 DataFrame
                
            Returns:
                pd.DataFrame: 정리된 DataFrame
        """
        pass
    
    @abstractmethod
    def insert_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
            DB 삽입 로직
            각 파서에서 테이블별 특화 삽입 구현
            
            Args:
                df: 삽입할 DataFrame
                
            Returns:
                Dict[str, Any]: 삽입 결과 (표준 형식)
        """
        pass