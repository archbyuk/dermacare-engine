#!/bin/bash

# 단일 Excel 파일 업로드 테스트 스크립트

echo "🔍 단일 Excel 파일 업로드 API 테스트"
echo "=================================="

# 파일 경로 설정
EXCEL_DIR="/Users/jeongjin-ug/Downloads/수가 DB 250813"
API_URL="http://localhost:9000/excel/upload-single"

# 사용 가능한 파일들
files=(
    "Enum.xlsx"
    "Consumables.xlsx" 
    "Global.xlsx"
    "Procedure_Element.xlsx"
    "Procedure_Bundle.xlsx"
    "Procedure_Sequence.xlsx"
    "Procedure_Class.xlsx"
    "Procedure_Custom.xlsx"
    "Info_Standard.xlsx"
    "Info_Event.xlsx"
    "Info_Membership.xlsx"
    "Product_Standard.xlsx"
    "Product_Event.xlsx"
    "Membership.xlsx"
)

# 파일 선택 (기본값: Enum.xlsx)
if [ -z "$1" ]; then
    echo "📁 사용법: $0 [파일명]"
    echo "📁 사용 가능한 파일들:"
    for file in "${files[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "🎯 기본값으로 Enum.xlsx를 업로드합니다..."
    FILENAME="Enum.xlsx"
else
    FILENAME="$1"
fi

FILE_PATH="$EXCEL_DIR/$FILENAME"

# 파일 존재 확인
if [ ! -f "$FILE_PATH" ]; then
    echo "❌ 파일을 찾을 수 없습니다: $FILE_PATH"
    exit 1
fi

echo "📤 업로드 파일: $FILENAME"
echo "🌐 API 엔드포인트: $API_URL"
echo ""

# API 호출
echo "⏳ 업로드 중..."
response=$(curl -s -X POST "$API_URL" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@$FILE_PATH")

# 응답 파싱 및 출력
echo "📋 응답 결과:"
echo "============"
echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✅ 상태: {data.get(\"status\", \"unknown\")}')
    print(f'📝 메시지: {data.get(\"message\", \"N/A\")}')
    
    file_info = data.get('file_info', {})
    print(f'📁 파일명: {file_info.get(\"filename\", \"N/A\")}')
    print(f'📏 파일 크기: {file_info.get(\"size_bytes\", 0):,} bytes')
    
    result = data.get('processing_result', {})
    if result.get('success'):
        print(f'🎯 테이블: {result.get(\"table_name\", \"N/A\")}')
        print(f'📊 처리된 행: {result.get(\"total_rows\", 0)}개')
        print(f'✅ 삽입된 행: {result.get(\"inserted_count\", 0)}개')
        print(f'❌ 오류 행: {result.get(\"error_count\", 0)}개')
    else:
        print(f'❌ 처리 실패: {result.get(\"error\", \"알 수 없는 오류\")}')
        
except json.JSONDecodeError:
    print('❌ JSON 응답 파싱 실패')
    print('원본 응답:', sys.stdin.read())
except Exception as e:
    print(f'❌ 오류 발생: {e}')
"

echo ""
echo "🏁 테스트 완료!"
