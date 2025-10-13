"""
    [ File Upload 엔드포인트 ]
    
    .xlsx, .xls 파일 업로드 엔드포인트를 관리합니다.
"""

from fastapi import APIRouter, HTTPException, Form

from ..services.download_service import download_service
from ..schema import UploadResponse
from ..services.parser_service import ParserService

# upload api 사용시 /upload 경로로 접근
router = APIRouter(tags=["File Upload"])

""" 파일 업로드 엔드포인트 """
@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file_json: str = Form(None),            # json 문자열로 받음 (파일 url들)
):
    try:
        parsered_layer = ParserService()
        
        # 파일 다운로드: file들의 url을 바탕으로 파일 다운로드 후 처리
        download_results = await download_service(file_json)
        
        # download_results: [
        #   {
        #       'file_name': '파일명 (type: str)',
        #       'file_data': '파일 데이터 (type: bytes)',
        #       'file_size': '파일 크기 (type: int)'
        #   }
        # ...
        # ]
        
        # 파일 파싱 후 데이터베이스에 삽입한 결과 및 에러 반환
        parsered_results, error_results = await parsered_layer.parser_process(download_results)

        # 에러 처리(실패한 파일의 수)
        failed_filenames = len(
            set(
                [error['filename'] for error in error_results]
            )
        )

        successful_filenames = len(
            set(
                [parsered_result['filename'] for parsered_result in parsered_results if parsered_result.get("success") == True]
                )
            )

        total_files = len(download_results) if download_results else 0

        # 응답 상태 결정
        if total_files == 0:
            raise HTTPException(
                status_code=400,
                detail="업로드할 파일이 없습니다"
            )
        
        # 모든 파일이 실패한 경우
        if successful_filenames == 0:
            raise HTTPException(
                status_code=500,
                detail=f"모든 파일 처리 실패 ({failed_filenames}개 파일 실패). 에러 목록을 확인하세요.",
            )
        
        # 일부 실패한 경우
        if failed_filenames > 0:
            status = "partial_success"
            message = f"{successful_filenames}개 성공, {failed_filenames}개 실패"
        # 모두 성공한 경우
        else:
            status = "completed"
            message = f"모든 파일 처리 완료 ({successful_filenames}개 파일)"
        
        # 응답 데이터 구성
        return UploadResponse(
            status=status,
            message=message,
            total_files=total_files,
            successful_files=successful_filenames,
            failed_files=failed_filenames,
            results=parsered_results,
            errors=error_results
        )
    

    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 업로드 중 오류 발생: {str(e)}"
        )
