"""
    [ 파일 데이터 다운로드 유틸리티 ]

    파일 데이터 다운로드 관련 공통 로직 및 유틸리티
"""

import aiohttp
import asyncio
from typing import Dict, Any, List
import json
from fastapi import HTTPException

async def download_service(file_json: str) -> List[Dict[str, Any]]:
    
    try:
        files_data = json.loads(file_json)

        # 모든 파일을 동시에 다운로드 (asyncio로 일괄 처리)
        async with aiohttp.ClientSession() as session:
            
            # 동시에 다운로드 할 파일 목록 생성
            download_tasks = []
            
            # 각 파일을 동시에 다운로드
            for file_data in files_data:
                task = asyncio.create_task(
                    # 파일 다운로드를 위한 함수 호출
                    download_file(session, file_data)
                    
                    # return: {
                    #   'file_name': '파일명',
                    #   'file_data': '파일 데이터',
                    #   'file_size': '파일 크기'
                    # }
                )
                
                download_tasks.append(task)

            # 모든 파일을 동시에 다운로드
            download_results = await asyncio.gather(*download_tasks)
            

            # 다운로드 결과 반환
            return download_results
    
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 다운로드 중 오류: {str(e)}")


# 파일 다운로드 함수: create_task에 넣기 위해 따로 정의
async def download_file(session: aiohttp.ClientSession, file_data: Dict):
    
    # file_data중 url을 가져와서 다운로드
    async with session.get(
        file_data['url']
    ) as download_response:

        # 다운로드 오류 발생 시 예외 발생
        download_response.raise_for_status()
        
        # 다운로드 된 파일 데이터 읽기
        file_content = await download_response.read()

        # 다운로드 결과 반환
        return {
            'file_name': file_data['name'],
            'file_data': file_content,
            'file_size': file_data['size']
        }