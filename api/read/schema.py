"""
    [ Read API 응답 스키마 정의 ]
    
    Read API 응답 스키마를 정의합니다.
"""

from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
from datetime import datetime


# ========== 목록 조회용 스키마 (최적화된 버전) ==========

class ProductListBase(BaseModel):
    """상품 목록 조회용 기본 정보 - 이전 구조 복원"""
    ID: int
    Product_Type: Optional[str] = None  # "standard" 또는 "event"
    Package_Type: Optional[str] = None
    Sell_Price: Optional[int] = None
    Original_Price: Optional[int] = None
    Product_Name: Optional[str] = None
    Product_Description: Optional[str] = None
    class_types: List[str] = []
    class_type_count: Optional[int] = 0
    procedure_names: List[str] = []
    Precautions: Optional[str] = None
    # 상세 정보 필드들
    bundle_details: List[Dict[str, Any]] = []
    custom_details: List[Dict[str, Any]] = []
    sequence_details: List[Dict[str, Any]] = []


class StandardProductList(ProductListBase):
    """표준 상품 목록 정보 - 최적화된 버전"""
    Product_Type: str = "standard"


class EventProductList(ProductListBase):
    """이벤트 상품 목록 정보 - 최적화된 버전"""
    Product_Type: str = "event"


# ========== 상세 조회용 스키마 (전체 정보) ==========

class ProductDetailBase(BaseModel):
    """상품 상세 조회용 기본 정보 - 전체 정보"""
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


class StandardProductDetail(ProductDetailBase):
    """표준 상품 상세 정보 - 전체 정보"""
    Product_Type: str = "standard"
    Standard_Start_Date: Optional[str] = None
    Standard_End_Date: Optional[str] = None


class EventProductDetail(ProductDetailBase):
    """이벤트 상품 상세 정보 - 전체 정보"""
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
    """상품 목록 응답 - 최적화된 버전"""
    status: str
    message: str
    data: List[Union[StandardProductList, EventProductList]]
    pagination: PaginationInfo


class ProductDetailResponse(BaseModel):
    """상품 상세 정보 응답 - 전체 정보"""
    success: bool = True
    message: str = "상품 상세 정보 조회 성공"
    product: Union[StandardProductDetail, EventProductDetail]


class ErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = False
    message: str
    detail: Optional[str] = None