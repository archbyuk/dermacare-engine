"""
    [ Upload API 응답 스키마 정의 ]
    
    Upload API 응답 스키마를 정의합니다.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class UploadResponse(BaseModel):
    """업로드 응답"""
    status: str
    message: str
    total_files: int
    successful_files: int
    failed_files: int
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]] = []  # 에러 목록 (기본값: 빈 리스트)

class ErrorResponse(BaseModel):
    """에러 응답"""
    status: str = "error"
    message: str
    detail: Optional[str] = None