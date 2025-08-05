#!/usr/bin/env python3
"""
테이블 데이터 초기화 스크립트
의존성 역순으로 모든 테이블의 데이터를 삭제합니다.
"""

import os
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models.enum import Enum
from db.models.consumables import Consumables
from db.models.global_config import Global
from db.models.procedure_element import ProcedureElement
from db.models.procedure_bundle import ProcedureBundle
from db.models.procedure_sequence import ProcedureSequence
from db.models.procedure_info import ProcedureInfo
from db.models.procedure_product import ProcedureProduct

def clear_all_tables():
    """의존성 역순으로 모든 테이블 데이터 삭제"""
    
    print("🗑️ 테이블 데이터 초기화 시작!")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # 의존성 역순으로 삭제 (Foreign Key 제약 조건 고려)
        tables_to_clear = [
            (ProcedureProduct, "ProcedureProduct"),
            (ProcedureInfo, "ProcedureInfo"), 
            (ProcedureSequence, "ProcedureSequence"),
            (ProcedureBundle, "ProcedureBundle"),
            (ProcedureElement, "ProcedureElement"),
            (Global, "Global"),
            (Consumables, "Consumables"),
            (Enum, "Enum"),
        ]
        
        total_deleted = 0
        
        for model_class, table_name in tables_to_clear:
            print(f"\n🧹 {table_name} 테이블 정리 중...")
            
            # 현재 레코드 수 확인
            count_before = db.query(model_class).count()
            print(f"   삭제 전: {count_before}개 레코드")
            
            if count_before > 0:
                # 모든 레코드 삭제
                deleted_count = db.query(model_class).delete()
                db.commit()
                
                # 삭제 후 확인
                count_after = db.query(model_class).count()
                print(f"   삭제 완료: {deleted_count}개 삭제됨")
                print(f"   삭제 후: {count_after}개 레코드")
                
                total_deleted += deleted_count
                
                if count_after == 0:
                    print(f"   ✅ {table_name} 테이블 완전히 비워짐")
                else:
                    print(f"   ⚠️ {table_name} 테이블에 {count_after}개 레코드 남음")
            else:
                print(f"   ✅ {table_name} 테이블 이미 비어있음")
        
        print("\n" + "="*50)
        print("🎯 테이블 초기화 완료!")
        print(f"📊 총 삭제된 레코드: {total_deleted}개")
        
        # 최종 확인
        print("\n📋 최종 테이블 상태:")
        for model_class, table_name in reversed(tables_to_clear):
            final_count = db.query(model_class).count()
            status = "✅ 비어있음" if final_count == 0 else f"⚠️ {final_count}개 남음"
            print(f"   {table_name:20}: {status}")
        
        print("\n🎉 모든 테이블이 초기화되었습니다!")
        print("이제 test_all_parsers_sequential.py를 실행할 수 있습니다.")
        
    except Exception as e:
        print(f"❌ 테이블 초기화 실패: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

def main():
    print("🔥 테이블 데이터 초기화 도구")
    print("⚠️ 이 작업은 모든 테이블의 데이터를 삭제합니다!")
    print()
    
    # 환경변수 확인
    required_env = ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"❌ 필수 환경변수가 설정되지 않았습니다: {missing_env}")
        print("다음 명령어로 환경변수를 설정하고 다시 실행하세요:")
        print("export DB_HOST=localhost && export DB_PORT=3309 && export DB_USER=root && export DB_PASSWORD='jung04671588!' && export DB_NAME=procedure_db")
        return
    
    print("✅ 환경변수 확인 완료")
    print(f"🔗 DB 연결 정보: {os.getenv('DB_USER')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    
    # 사용자 확인
    print("\n" + "="*50)
    print("⚠️ 경고: 이 작업은 되돌릴 수 없습니다!")
    print("모든 테이블의 데이터가 영구적으로 삭제됩니다.")
    
    response = input("\n계속하시겠습니까? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        clear_all_tables()
    else:
        print("❌ 작업이 취소되었습니다.")

if __name__ == "__main__":
    main()