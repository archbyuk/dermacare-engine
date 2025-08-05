#!/usr/bin/env python3
"""
전체 Excel 파서 순차 테스트 스크립트
의존성 순서에 맞게 모든 파일을 순서대로 파싱하고 DB에 삽입합니다.
"""

import asyncio
import os
import time
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session

async def test_single_parser(filename: str, table_name: str) -> Tuple[bool, Dict[str, Any]]:
    """단일 파서 테스트 함수"""
    file_path = f"/Users/jeongjin-ug/Downloads/수가DB_250804/{filename}"
    
    print(f"\n🧪 {table_name} 파서 테스트 시작!")
    print(f"📁 파일: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ 파일이 존재하지 않습니다: {file_path}")
        return False, {"success": False, "table_name": table_name, "error": "파일 없음"}
    
    print(f"✅ 파일 확인 완료 (크기: {os.path.getsize(file_path)} bytes)")
    
    try:
        print("\n📖 파일 읽는 중...")
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        print(f"✅ 파일 읽기 완료 ({len(file_bytes)} bytes)")
        
        print("\n🔗 데이터베이스 연결 중...")
        from db.session import SessionLocal
        db = SessionLocal()
        print("✅ 데이터베이스 연결 성공!")
        
        print("\n🔧 ParsersManager 초기화...")
        from crud.excel_parser.parsers_manager import ParsersManager
        manager = ParsersManager(db)
        print("✅ 초기화 완료!")
        
        print(f"\n🚀 {table_name} 파일 처리 중...")
        start_time = time.time()
        result = await manager.process_excel_file(filename, file_bytes)
        end_time = time.time()
        
        print(f"\n📊 처리 결과 ({end_time - start_time:.2f}초):")
        print(f"✅ 성공 여부: {result['success']}")
        print(f"📋 테이블명: {result['table_name']}")
        print(f"📈 총 행 수: {result['total_rows']}")
        print(f"✅ 삽입된 레코드: {result['inserted_count']}")
        print(f"🔄 업데이트된 레코드: {result.get('updated_count', 0)}")
        print(f"❌ 에러 발생: {result['error_count']}")
        
        if result.get('errors'):
            print(f"\n❌ 에러 목록:")
            for i, error in enumerate(result['errors'][:3]):
                print(f"   {i+1}. {error}")
            if len(result['errors']) > 3:
                print(f"   ... 및 {len(result['errors'])-3}개 더")
        
        db.close()
        return result['success'], result
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        try:
            db.rollback()
            db.close()
        except:
            pass
        return False, {"success": False, "table_name": table_name, "error": str(e)}

async def main():
    """메인 테스트 함수"""
    print("🚀 전체 Excel 파서 순차 테스트 시작!")
    print("=" * 60)
    
    # 의존성 순서대로 정의 (SQL 스키마 순서)
    parsers_sequence = [
        ("Enum.xlsx", "Enum"),
        ("Consumables.xlsx", "Consumables"),
        ("Global.xlsx", "Global"),
        ("Procedure_Element.xlsx", "ProcedureElement"),
        ("Procedure_Bundle.xlsx", "ProcedureBundle"),
        ("Procedure_Sequence.xlsx", "ProcedureSequence"),
        ("Procedure_Info.xlsx", "ProcedureInfo"),
        ("Procedure_Product.xlsx", "ProcedureProduct"),
    ]
    
    overall_results = {}
    total_inserted = 0
    total_updated = 0
    total_errors = 0
    failed_parsers = []
    
    start_total_time = time.time()
    
    for i, (filename, table_name) in enumerate(parsers_sequence, 1):
        print(f"\n{'='*20} [{i}/{len(parsers_sequence)}] {table_name} {'='*20}")
        
        success, result = await test_single_parser(filename, table_name)
        overall_results[table_name] = "✅ 성공" if success else "❌ 실패"
        
        if success:
            total_inserted += result.get('inserted_count', 0)
            total_updated += result.get('updated_count', 0)
            total_errors += result.get('error_count', 0)
            print(f"🎯 {table_name}: ✅ 성공")
        else:
            failed_parsers.append(table_name)
            print(f"🎯 {table_name}: ❌ 실패")
            
        # 실패 시 잠시 대기
        if not success:
            print("⚠️ 실패 - 1초 대기 후 계속...")
            time.sleep(1)
    
    end_total_time = time.time()
    total_time = end_total_time - start_total_time
    
    print("\n" + "="*60)
    print("🎯 전체 테스트 결과 요약")
    print("="*60)
    
    successful_count = 0
    for table, status in overall_results.items():
        print(f"   {table:20}: {status}")
        if status == "✅ 성공":
            successful_count += 1
    
    print(f"\n📊 성공률: {successful_count}/{len(parsers_sequence)}개 ({successful_count/len(parsers_sequence)*100:.1f}%)")
    print(f"⏱️ 총 소요 시간: {total_time:.2f}초")
    print(f"✅ 총 삽입된 레코드: {total_inserted}개")
    print(f"🔄 총 업데이트된 레코드: {total_updated}개")
    print(f"❌ 총 에러 발생: {total_errors}개")
    
    if successful_count == len(parsers_sequence):
        print("\n🎉 모든 파서 테스트 성공!")
        print("🎊 데이터베이스에 모든 데이터가 성공적으로 삽입되었습니다!")
    else:
        print(f"\n⚠️ {len(failed_parsers)}개 파서 실패:")
        for failed in failed_parsers:
            print(f"   - {failed}")
        print("\n💡 실패한 파서들을 개별적으로 확인해보세요.")
    
    print("\n" + "="*60)
    print("테스트 완료!")

if __name__ == "__main__":
    print("🔥 Excel 파서 종합 테스트")
    print("📝 의존성 순서대로 모든 파일을 순차 처리합니다.")
    print("⚠️ 테이블 데이터가 초기화되었는지 확인하세요!")
    print()
    
    # 환경변수 확인
    required_env = ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"❌ 필수 환경변수가 설정되지 않았습니다: {missing_env}")
        print("다음 명령어로 환경변수를 설정하고 다시 실행하세요:")
        print("export DB_HOST=localhost && export DB_PORT=3309 && export DB_USER=root && export DB_PASSWORD='jung04671588!' && export DB_NAME=procedure_db")
        exit(1)
    
    print("✅ 환경변수 확인 완료")
    print(f"🔗 DB 연결 정보: {os.getenv('DB_USER')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    
    asyncio.run(main())