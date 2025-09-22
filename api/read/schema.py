"""
    [ Read API 응답 스키마 정의 ]
    
    Read API 응답 스키마를 정의합니다.
"""

from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime


class ProductBase(BaseModel):
    """상품 기본 정보"""
    ID: int
    Product_Type: Optional[str] = None  # "standard" 또는 "event"
    Package_Type: Optional[str] = None
    Sell_Price: Optional[int] = None
    Original_Price: Optional[int] = None
    Validity_Period: Optional[int] = None
    Product_Name: Optional[str] = None
    Product_Description: Optional[str] = None
    Precautions: Optional[str] = None
    procedure_names: List[str] = []
    procedure_count: Optional[int] = 0
    class_types: List[str] = []
    class_type_count: Optional[int] = 0


class StandardProduct(ProductBase):
    """표준 상품 정보"""
    Product_Type: str = "standard"
    Standard_Start_Date: Optional[str] = None
    Standard_End_Date: Optional[str] = None


class EventProduct(ProductBase):
    """이벤트 상품 정보"""
    Product_Type: str = "event"
    Event_Start_Date: Optional[str] = None
    Event_End_Date: Optional[str] = None


### Read API 응답 스키마 ###

class PaginationInfo(BaseModel):
    """페이지네이션 정보"""
    page: int
    page_size: int
    total_count: int
    total_pages: int

class ProductListResponse(BaseModel):
    """상품 목록 응답"""
    status: str
    message: str
    data: List[Union[StandardProduct, EventProduct]]
    pagination: PaginationInfo


class ProductDetailResponse(BaseModel):
    """상품 상세 정보 응답"""
    success: bool = True
    message: str = "상품 상세 정보 조회 성공"
    product: Union[StandardProduct, EventProduct]


class ErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = False
    message: str
    detail: Optional[str] = None
