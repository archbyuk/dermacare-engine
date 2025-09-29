"""
    [ Upload API 응답 스키마 정의 ]
    
    Upload API 응답 스키마를 정의합니다.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class SingleUploadResponse(BaseModel):
    """단일 업로드 응답"""
    status: str
    message: str
    file_info: Dict[str, Any]
    processing_result: Dict[str, Any]

class MultipleUploadResponse(BaseModel):
    """다중 업로드 응답"""
    status: str
    message: str
    total_files: int
    successful_files: int
    failed_files: int
    results: List[Dict[str, Any]]
    cleared_tables: Optional[Dict[str, int]] = None

class UploadResponse(BaseModel):
    """업로드 응답"""
    status: str
    message: str
    total_files: int
    successful_files: int
    failed_files: int
    results: List[Dict[str, Any]]
    cleared_tables: Optional[Dict[str, int]] = None

class ErrorResponse(BaseModel):
    """에러 응답"""
    status: str = "error"
    message: str
    detail: Optional[str] = None
