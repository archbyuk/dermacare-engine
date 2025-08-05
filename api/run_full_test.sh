#!/bin/bash

# Excel 파서 전체 테스트 실행 스크립트

echo "🔥 Excel 파서 전체 테스트 시작!"
echo "=================================="

# 환경변수 설정
export DB_HOST=localhost
export DB_PORT=3309
export DB_USER=root
export DB_PASSWORD='jung04671588!'
export DB_NAME=procedure_db

echo "✅ 환경변수 설정 완료"
echo "🔗 DB: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo

# 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 가상환경 활성화됨: $VIRTUAL_ENV"
else
    echo "⚠️ 가상환경이 활성화되지 않았습니다."
    echo "다음 명령어로 가상환경을 활성화하세요:"
    echo "source venv/bin/activate"
    echo
fi

echo "=================================="
echo "1단계: 테이블 데이터 초기화"
echo "=================================="
python3 clear_tables.py

echo
echo "=================================="
echo "2단계: 전체 파서 순차 테스트"
echo "=================================="
python3 test_all_parsers_sequential.py

echo
echo "🎉 전체 테스트 완료!"