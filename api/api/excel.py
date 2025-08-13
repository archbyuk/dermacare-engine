"""
    Excel 파일 업로드 및 파싱 API
    테이블 간 의존성이 없으므로 순서에 상관없이 처리 가능
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import asyncio

from db.session import get_db
from crud.excel_parser.parsers_manager import ParsersManager

excel_router = APIRouter(
    prefix="/excel",
    tags=["Excel Processing"]
)

def validate_excel_file(file: UploadFile) -> None:
    """Excel 파일 유효성 검증"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail=f"'{file.filename}'은(는) Excel 파일이 아닙니다. (.xlsx, .xls 파일만 지원)"
        )

def validate_excel_files(files: List[UploadFile]) -> None:
    """다중 Excel 파일 유효성 검증"""
    for file in files:
        validate_excel_file(file)

async def process_single_file(file: UploadFile, manager: ParsersManager) -> Dict[str, Any]:
    """단일 파일 처리"""
    try:
        contents = await file.read()
        result = await manager.process_excel_file(file.filename, contents)
        
        return {
            "filename": file.filename,
            "status": "success",
            "result": result,
            "size_bytes": len(contents)
        }
    except Exception as e:
        return {
            "filename": file.filename,
            "status": "failed",
            "error": str(e)
        }

@excel_router.post("/upload-single")
async def upload_single_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    단일 Excel 파일 업로드 및 파싱
    
    파일명을 기반으로 적절한 파서를 자동 선택하여 처리합니다.
    """
    validate_excel_file(file)
    
    try:
        manager = ParsersManager(db)
        result = await process_single_file(file, manager)
        
        if result["status"] == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"파일 처리 실패: {result['error']}"
            )
        
        return {
            "status": "success",
            "message": f"'{file.filename}' 파일 처리 완료",
            "file_info": {
                "filename": file.filename,
                "size_bytes": result["size_bytes"]
            },
            "processing_result": result["result"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 처리 중 오류 발생: {str(e)}"
        )

@excel_router.post("/upload-multiple")
async def upload_multiple_excel(
    files: List[UploadFile] = File(...),
    clear_tables: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    다중 Excel 파일 업로드 및 병렬 파싱
    
    테이블 간 의존성이 없으므로 모든 파일을 병렬로 처리합니다.
    
    Parameters:
    - files: 업로드할 Excel 파일들
    - clear_tables: True일 경우 모든 테이블 데이터를 삭제 후 새로 삽입
    """
    validate_excel_files(files)
    
    try:
        cleared_counts = {}
        
        # 테이블 초기화 (옵션)
        if clear_tables:
            # 모든 ORM 모델을 동적으로 가져와서 처리
            from db import (
                Consumables, Enum, Global,
                InfoEvent, InfoMembership, InfoStandard,
                Membership,
                ProcedureElement, ProcedureClass, ProcedureBundle, 
                ProcedureCustom, ProcedureSequence,
                ProductEvent, ProductStandard
            )
            
            # 모든 모델을 리스트로 관리
            all_models = [
                (Consumables, "Consumables"),
                (Enum, "Enum"),
                (Global, "Global"),
                (InfoEvent, "Info_Event"),
                (InfoMembership, "Info_Membership"),
                (InfoStandard, "Info_Standard"),
                (Membership, "Membership"),
                (ProcedureElement, "Procedure_Element"),
                (ProcedureClass, "Procedure_Class"),
                (ProcedureBundle, "Procedure_Bundle"),
                (ProcedureCustom, "Procedure_Custom"),
                (ProcedureSequence, "Procedure_Sequence"),
                (ProductEvent, "Product_Event"),
                (ProductStandard, "Product_Standard"),
            ]
            
            # 모든 테이블 데이터 삭제
            for model_class, table_name in all_models:
                count = db.query(model_class).count()
                db.query(model_class).delete()
                cleared_counts[table_name] = count
            
            db.commit()
        
        # 병렬 처리
        manager = ParsersManager(db)
        tasks = [process_single_file(file, manager) for file in files]
        results = await asyncio.gather(*tasks)
        
        # 결과 분석
        success_count = sum(1 for r in results if r["status"] == "success")
        failed_count = len(results) - success_count
        
        response_data = {
            "status": "completed",
            "message": f"다중 파일 처리 완료 (성공: {success_count}, 실패: {failed_count})",
            "summary": {
                "total_files": len(files),
                "success_count": success_count,
                "failed_count": failed_count
            },
            "results": results
        }
        
        # 테이블 초기화 정보 추가
        if clear_tables:
            response_data["cleared_tables"] = cleared_counts
            response_data["message"] = f"테이블 초기화 후 {response_data['message']}"
        
        return response_data
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"다중 파일 처리 중 오류 발생: {str(e)}"
        )

@excel_router.get("/supported-files")
def get_supported_files():
    """
    지원되는 Excel 파일 목록 조회
    
    현재 파서가 지원하는 파일명들을 반환합니다.
    """
    supported_files = [
        "Consumables.xlsx",
        "Enum.xlsx", 
        "Global.xlsx",
        "Info_Event.xlsx",
        "Info_Membership.xlsx",
        "Info_Standard.xlsx",
        "Membership.xlsx",
        "Procedure_Bundle.xlsx",
        "Procedure_Class.xlsx",
        "Procedure_Custom.xlsx",
        "Procedure_Element.xlsx",
        "Procedure_Sequence.xlsx",
        "Product_Event.xlsx",
        "Product_Standard.xlsx"
    ]
    
    return {
        "status": "success",
        "supported_files": supported_files,
        "total_count": len(supported_files),
        "message": "현재 지원되는 Excel 파일 목록입니다."
    }