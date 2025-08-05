"""
실제 데이터베이스에 Enum 데이터 삽입 테스트
실제 DB 연결 + 실제 파일 + 실제 삽입
"""

import asyncio
import os
from sqlalchemy.orm import Session

async def test_enum_db_insert():
    """실제 DB에 Enum 데이터 삽입 테스트"""
    
    file_path = "/Users/jeongjin-ug/Downloads/수가DB_250804/Enum.xlsx"
    
    print(f"🧪 실제 DB 삽입 테스트 시작!")
    print(f"📁 파일: {file_path}")
    
    # 1. 파일 존재 확인
    if not os.path.exists(file_path):
        print(f"❌ 파일이 존재하지 않습니다: {file_path}")
        return False
    
    print(f"✅ 파일 확인 완료 (크기: {os.path.getsize(file_path)} bytes)")
    
    try:
        # 2. 파일 읽기
        print("\n📖 파일 읽는 중...")
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        print(f"✅ 파일 읽기 완료 ({len(file_bytes)} bytes)")
        
        # 3. 실제 DB 세션 생성
        print("\n🔗 데이터베이스 연결 중...")
        from db import get_db, SessionLocal
        
        # 실제 DB 세션 생성
        db = SessionLocal()
        print("✅ 데이터베이스 연결 성공!")
        
        # 4. EnumParser 초기화 (실제 DB 세션 사용)
        print("\n🔧 EnumParser 초기화...")
        from crud.excel_parser.parsers.enum_parser import EnumParser
        parser = EnumParser(db)
        print(f"✅ 초기화 완료 (테이블: {parser.table_name})")
        
        # 5. 전체 워크플로우 실행 (실제 삽입 포함)
        print("\n🚀 전체 워크플로우 실행 중...")
        print("   1️⃣ 엑셀 파싱...")
        print("   2️⃣ 데이터 검증...")
        print("   3️⃣ 데이터 정리...")
        print("   4️⃣ 실제 DB 삽입...")
        
        result = await parser.process_file(file_bytes)
        
        # 6. 결과 출력
        print(f"\n📊 삽입 결과:")
        print(f"✅ 성공 여부: {result['success']}")
        print(f"📋 테이블명: {result['table_name']}")
        print(f"📈 총 행 수: {result['total_rows']}")
        print(f"✅ 삽입된 레코드: {result['inserted_count']}")
        print(f"🔄 업데이트된 레코드: {result.get('updated_count', 0)}")
        print(f"❌ 에러 발생: {result['error_count']}")
        
        if result.get('processed_classifications'):
            print(f"🏷️ 처리된 분류들: {result['processed_classifications']}")
        
        if result.get('errors'):
            print(f"\n❌ 에러 목록:")
            for i, error in enumerate(result['errors'][:5]):  # 최대 5개만 표시
                print(f"   {i+1}. {error}")
            if len(result['errors']) > 5:
                print(f"   ... 및 {len(result['errors'])-5}개 더")
        
        # 7. DB에서 실제 데이터 확인
        print(f"\n🔍 DB에서 실제 데이터 확인...")
        from db.models.enum import Enum
        
        # 각 분류별 개수 확인
        classification_types = ['ClassMajor', 'ClassSub', 'ClassDetail', 'ClassType', 
                              'PositionType', 'UnitType', 'PackageType']
        
        for class_type in classification_types:
            count = db.query(Enum).filter(Enum.Type == class_type).count()
            print(f"   📊 {class_type}: {count}개")
            
            # 샘플 데이터 3개 보기
            samples = db.query(Enum).filter(Enum.Type == class_type).limit(3).all()
            for sample in samples:
                print(f"      - ID={sample.ID}, Code='{sample.Code}'")
        
        total_count = db.query(Enum).count()
        print(f"\n🎯 총 Enum 레코드 수: {total_count}개")
        
        # 8. 세션 정리
        db.close()
        
        print(f"\n🎉 실제 DB 삽입 테스트 완료!")
        return result['success']
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        
        # 에러 발생시 세션 정리
        try:
            db.rollback()
            db.close()
        except:
            pass
            
        return False

if __name__ == "__main__":
    result = asyncio.run(test_enum_db_insert())
    if result:
        print("\n✅ 전체 테스트 성공!")
    else:
        print("\n❌ 테스트 실패!")