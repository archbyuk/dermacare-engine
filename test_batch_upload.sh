#!/bin/bash

# 배치 Excel 파일 업로드 테스트 스크립트 (테이블 초기화 포함)

echo "🔍 배치 Excel 파일 업로드 API 테스트"
echo "==================================="

# 파일 경로 설정
EXCEL_DIR="/Users/jeongjin-ug/Downloads/수가 DB 250813"
API_URL="http://localhost:9000/excel/upload-batch"

# 테이블 초기화 여부 (기본값: true)
CLEAR_TABLES="${1:-true}"

echo "🗑️  테이블 초기화: $CLEAR_TABLES"
echo "🌐 API 엔드포인트: $API_URL"
echo ""

# 업로드할 파일들
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

echo "📁 업로드할 파일들:"
for file in "${files[@]}"; do
    if [ -f "$EXCEL_DIR/$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (파일 없음)"
    fi
done

echo ""

# 확인 메시지
if [ "$CLEAR_TABLES" = "true" ]; then
    echo "⚠️  경고: 모든 테이블 데이터가 삭제됩니다!"
    echo "계속하시겠습니까? (y/N): "
    read -r confirmation
    if [[ ! "$confirmation" =~ ^[Yy]$ ]]; then
        echo "❌ 작업이 취소되었습니다."
        exit 0
    fi
fi

echo "⏳ 배치 업로드 시작..."

# curl 명령어 구성
curl_cmd="curl -s -X POST \"$API_URL\" -H \"accept: application/json\" -H \"Content-Type: multipart/form-data\" -F \"clear_tables=$CLEAR_TABLES\""

for file in "${files[@]}"; do
    file_path="$EXCEL_DIR/$file"
    if [ -f "$file_path" ]; then
        curl_cmd="$curl_cmd -F \"files=@$file_path\""
    fi
done

# API 호출 실행
response=$(eval $curl_cmd)

# 응답 파싱 및 출력
echo "📋 배치 업로드 결과:"
echo "==================="
echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✅ 상태: {data.get(\"status\", \"unknown\")}')
    print(f'📝 메시지: {data.get(\"message\", \"N/A\")}')
    
    # 테이블 초기화 정보
    if 'cleared_tables' in data:
        print()
        print('🗑️  초기화된 테이블들:')
        for table, count in data['cleared_tables'].items():
            print(f'   - {table}: {count}개 행 삭제')
    
    summary = data.get('summary', {})
    print()
    print('📊 업로드 요약:')
    print(f'   총 파일: {summary.get(\"total_files\", 0)}개')
    print(f'   ✅ 성공: {summary.get(\"success_count\", 0)}개')
    print(f'   ❌ 실패: {summary.get(\"failed_count\", 0)}개')
    
    print()
    print('📁 처리 순서:')
    for i, filename in enumerate(data.get('processing_order', []), 1):
        print(f'   {i}. {filename}')
    
    print()
    print('📋 상세 결과:')
    for result in data.get('results', []):
        filename = result.get('filename', 'N/A')
        status = result.get('status', 'unknown')
        
        if status == 'success':
            proc_result = result.get('result', {})
            if proc_result.get('success'):
                table_name = proc_result.get('table_name', 'N/A')
                inserted = proc_result.get('inserted_count', 0)
                print(f'   ✅ {filename} → {table_name} ({inserted}개 행 삽입)')
            else:
                print(f'   ❌ {filename} → 처리 실패')
        else:
            error = result.get('error', '알 수 없는 오류')
            print(f'   ❌ {filename} → {error}')
            
except json.JSONDecodeError:
    print('❌ JSON 응답 파싱 실패')
    print('원본 응답:', sys.stdin.read())
except Exception as e:
    print(f'❌ 오류 발생: {e}')
"

echo ""
echo "🏁 배치 업로드 테스트 완료!"
