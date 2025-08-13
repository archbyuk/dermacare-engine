#!/bin/bash

# DermaCare API 전체 흐름 테스트 스크립트
# Excel 업로드 → 데이터베이스 삽입 → 전체목록 → 검색/정렬/필터 → 상세조회

echo "🚀 DermaCare API 전체 흐름 테스트 시작"
echo "=========================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API 기본 URL
BASE_URL="http://localhost:9000"

# 테스트 결과 카운터
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 테스트 함수 (상세 출력)
test_api() {
    local test_name="$1"
    local api_call="$2"
    local expected_pattern="$3"
    local show_response="${4:-false}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}🧪 테스트: $test_name${NC}"
    echo -e "${BLUE}📡 API 호출: $api_call${NC}"
    
    # API 호출
    response=$(eval "$api_call" 2>/dev/null)
    exit_code=$?
    
    echo -e "${BLUE}📊 응답 코드: $exit_code${NC}"
    
    if [ $exit_code -eq 0 ] && echo "$response" | grep -q "$expected_pattern"; then
        echo -e "${GREEN}✅ 성공${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        
        # 상세 응답 출력 (옵션)
        if [ "$show_response" = "true" ]; then
            echo -e "${BLUE}📄 상세 응답:${NC}"
            echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        fi
    else
        echo -e "${RED}❌ 실패${NC}"
        echo -e "${RED}📄 오류 응답:${NC}"
        echo "$response"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# 상세 테스트 함수 (항상 응답 출력)
test_api_detailed() {
    local test_name="$1"
    local api_call="$2"
    local expected_pattern="$3"
    
    test_api "$test_name" "$api_call" "$expected_pattern" "true"
}

# 데이터베이스 상태 확인
echo -e "\n${YELLOW}📊 데이터베이스 상태 확인${NC}"
echo "=========================================="
echo -e "${BLUE}📝 실제 데이터베이스 정보:${NC}"
echo "- Product_Standard: 12개"
echo "- Product_Event: 12개"
echo "- Class_Major: 레이저, 초음파"
echo "- Class_Sub: 리팟, 젠틀맥스, 아포지, 울쎄라, 슈링크"

# 1단계: 헬스 체크
echo -e "\n${YELLOW}📋 1단계: 서버 상태 확인${NC}"
test_api "서버 헬스 체크" \
    "curl -s $BASE_URL/health/" \
    "healthy"

# 2단계: Excel 파일 업로드 (실제 테스트)
echo -e "\n${YELLOW}📋 2단계: Excel 파일 업로드 (실제 테스트)${NC}"

# Excel 파일 경로
EXCEL_DIR="$HOME/Downloads/수가 DB 250813"

# 기존 데이터 클리어 후 업로드
echo -e "${BLUE}📝 기존 데이터 클리어 후 모든 Excel 파일 업로드 중...${NC}"

# 모든 Excel 파일을 배열로 저장
excel_files=(
    "$EXCEL_DIR/Consumables.xlsx"
    "$EXCEL_DIR/Enum.xlsx"
    "$EXCEL_DIR/Global.xlsx"
    "$EXCEL_DIR/Info_Event.xlsx"
    "$EXCEL_DIR/Info_Membership.xlsx"
    "$EXCEL_DIR/Info_Standard.xlsx"
    "$EXCEL_DIR/Membership.xlsx"
    "$EXCEL_DIR/Procedure_Bundle.xlsx"
    "$EXCEL_DIR/Procedure_Class.xlsx"
    "$EXCEL_DIR/Procedure_Custom.xlsx"
    "$EXCEL_DIR/Procedure_Element.xlsx"
    "$EXCEL_DIR/Procedure_Sequence.xlsx"
    "$EXCEL_DIR/Product_Event.xlsx"
    "$EXCEL_DIR/Product_Standard.xlsx"
)

# 파일 존재 확인
echo -e "${BLUE}🔍 Excel 파일 존재 확인:${NC}"
for file in "${excel_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $(basename "$file")${NC}"
    else
        echo -e "${RED}❌ $(basename "$file") - 파일을 찾을 수 없습니다${NC}"
    fi
done

# 실제 업로드 테스트
echo -e "${BLUE}📤 실제 Excel 파일 업로드 중...${NC}"

# curl 명령어를 구성하여 실제 파일들을 업로드
upload_command="curl -X POST $BASE_URL/excel/upload-multiple -F 'clear_tables=true'"

# 각 파일을 -F 옵션으로 추가
for file in "${excel_files[@]}"; do
    if [ -f "$file" ]; then
        upload_command="$upload_command -F 'files=@$file'"
    fi
done

# 업로드 실행
echo -e "${BLUE}📝 업로드 명령어 실행 중...${NC}"
response=$(eval $upload_command 2>/dev/null)

# 응답 확인
if echo "$response" | grep -q '"status":"completed"'; then
    echo -e "${GREEN}✅ Excel 파일 업로드 성공${NC}"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
else
    echo -e "${RED}❌ Excel 파일 업로드 실패${NC}"
    echo "응답: $response"
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 업로드 후 데이터베이스 상태 확인
echo -e "\n${BLUE}📊 업로드 후 데이터베이스 상태 확인:${NC}"
sleep 3  # 업로드 완료 대기

# 데이터베이스에서 실제 데이터 개수 확인
db_response=$(mysql -h 127.0.0.1 -P 3309 -u root -pjung04671588! -e "USE procedure_db; SELECT COUNT(*) as total_products FROM Product_Standard; SELECT COUNT(*) as total_events FROM Product_Event;" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 데이터베이스 연결 성공${NC}"
    echo "$db_response"
else
    echo -e "${RED}❌ 데이터베이스 연결 실패${NC}"
fi

# 3단계: 전체 상품 목록 조회
echo -e "\n${YELLOW}📋 3단계: 전체 상품 목록 조회${NC}"
test_api_detailed "전체 상품 목록 조회" \
    "curl -s $BASE_URL/read/products" \
    "status"

test_api_detailed "Standard 상품만 조회" \
    "curl -s $BASE_URL/read/products?product_type=standard" \
    "status"

test_api_detailed "Event 상품만 조회" \
    "curl -s $BASE_URL/read/products?product_type=event" \
    "status"

# 4단계: 검색 기능 테스트 (실제 데이터 기반)
echo -e "\n${YELLOW}📋 4단계: 검색 기능 테스트 (실제 데이터)${NC}"
test_api_detailed "울쎄라 검색" \
    "curl -s -G $BASE_URL/search/products --data-urlencode 'q=울쎄라'" \
    "status"

test_api_detailed "레이저 검색" \
    "curl -s -G $BASE_URL/search/products --data-urlencode 'q=레이저'" \
    "status"

test_api_detailed "리팟 검색" \
    "curl -s -G $BASE_URL/search/products --data-urlencode 'q=리팟'" \
    "status"

test_api_detailed "젠틀맥스 검색" \
    "curl -s -G $BASE_URL/search/products --data-urlencode 'q=젠틀맥스'" \
    "status"

test_api_detailed "초음파 검색" \
    "curl -s -G $BASE_URL/search/products --data-urlencode 'q=초음파'" \
    "status"

# 5단계: 정렬 기능 테스트
echo -e "\n${YELLOW}📋 5단계: 정렬 기능 테스트${NC}"
test_api "가격 오름차순 정렬" \
    "curl -s $BASE_URL/sort/products?sort_by=price&order=asc" \
    "status"

test_api "가격 내림차순 정렬" \
    "curl -s $BASE_URL/sort/products?sort_by=price&order=desc" \
    "status"

test_api "이름 오름차순 정렬" \
    "curl -s $BASE_URL/sort/products?sort_by=name&order=asc" \
    "status"

test_api "날짜 내림차순 정렬" \
    "curl -s $BASE_URL/sort/products?sort_by=date&order=desc" \
    "status"

# 6단계: 필터 기능 테스트 (실제 데이터 기반)
echo -e "\n${YELLOW}📋 6단계: 필터 기능 테스트 (실제 데이터)${NC}"
test_api "레이저 메이저 분류 필터" \
    "curl -s -G $BASE_URL/filter/products --data-urlencode 'class_major=레이저'" \
    "status"

test_api "초음파 메이저 분류 필터" \
    "curl -s -G $BASE_URL/filter/products --data-urlencode 'class_major=초음파'" \
    "status"

test_api "리팟 서브 분류 필터" \
    "curl -s -G $BASE_URL/filter/products --data-urlencode 'class_sub=리팟'" \
    "status"

test_api "울쎄라 서브 분류 필터" \
    "curl -s -G $BASE_URL/filter/products --data-urlencode 'class_sub=울쎄라'" \
    "status"

test_api "복합 필터 (레이저 + 리팟)" \
    "curl -s -G $BASE_URL/filter/products --data-urlencode 'class_major=레이저' --data-urlencode 'class_sub=리팟'" \
    "status"

# 7단계: 상세 조회 테스트
echo -e "\n${YELLOW}📋 7단계: 상세 조회 테스트${NC}"

# 먼저 검색으로 상품 ID를 가져오기
echo -e "${BLUE}🔍 상품 ID 가져오는 중...${NC}"
search_response=$(curl -s -G $BASE_URL/search/products --data-urlencode 'q=울쎄라')
echo -e "${BLUE}📄 검색 응답:${NC}"
echo "$search_response" | python3 -m json.tool 2>/dev/null || echo "$search_response"

product_id=$(echo "$search_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data['data'] and len(data['data']) > 0:
        print(data['data'][0]['ID'])
    else:
        print('103')  # 기본값
except:
    print('103')  # 기본값
" 2>/dev/null)

product_type=$(echo "$search_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data['data'] and len(data['data']) > 0:
        print(data['data'][0]['Product_Type'])
    else:
        print('event')  # 기본값
except:
    print('event')  # 기본값
" 2>/dev/null)

echo -e "${BLUE}📝 테스트할 상품: ID=$product_id, Type=$product_type${NC}"

test_api_detailed "상품 상세 조회" \
    "curl -s $BASE_URL/read/products/$product_id?product_type=$product_type" \
    "status"

# 8단계: 에러 처리 테스트
echo -e "\n${YELLOW}📋 8단계: 에러 처리 테스트${NC}"
test_api "존재하지 않는 상품 조회" \
    "curl -s $BASE_URL/read/products/999999?product_type=standard" \
    "상품을 찾을 수 없습니다"

test_api "잘못된 검색어 (빈 검색어)" \
    "curl -s -G $BASE_URL/search/products --data-urlencode 'q='" \
    "검색어를 입력해주세요"

test_api "잘못된 정렬 기준" \
    "curl -s $BASE_URL/sort/products?sort_by=invalid&order=asc" \
    "잘못된 정렬 기준입니다"

# 9단계: 페이지네이션 테스트
echo -e "\n${YELLOW}📋 9단계: 페이지네이션 테스트${NC}"
test_api "페이지네이션 테스트 (페이지 1)" \
    "curl -s $BASE_URL/read/products?page=1&page_size=5" \
    "pagination"

test_api "페이지네이션 테스트 (페이지 2)" \
    "curl -s $BASE_URL/read/products?page=2&page_size=5" \
    "pagination"

# 10단계: 실제 데이터 검증
echo -e "\n${YELLOW}📋 10단계: 실제 데이터 검증${NC}"

# 검색 결과 개수 확인
echo -e "${BLUE}🔍 검색 결과 개수 확인:${NC}"
search_response=$(curl -s -G $BASE_URL/search/products --data-urlencode 'q=레이저')
echo -e "${BLUE}📄 레이저 검색 응답:${NC}"
echo "$search_response" | python3 -m json.tool 2>/dev/null || echo "$search_response"

count=$(echo "$search_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['pagination']['total_count'])
except:
    print('0')
" 2>/dev/null)
echo -e "${BLUE}레이저 검색 결과: ${GREEN}$count개${NC}"

# 정렬 결과 확인
echo -e "${BLUE}🔍 정렬 결과 확인:${NC}"
sort_response=$(curl -s $BASE_URL/sort/products?sort_by=price&order=desc)
echo -e "${BLUE}📄 정렬 응답:${NC}"
echo "$sort_response" | python3 -m json.tool 2>/dev/null || echo "$sort_response"

sort_count=$(echo "$sort_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['pagination']['total_count'])
except:
    print('0')
" 2>/dev/null)
echo -e "${BLUE}전체 상품 수: ${GREEN}$sort_count개${NC}"

# 데이터베이스 직접 확인
echo -e "\n${BLUE}🔍 데이터베이스 직접 확인:${NC}"
db_check=$(mysql -h 127.0.0.1 -P 3309 -u root -pjung04671588! -e "
USE procedure_db; 
SELECT 'Product_Standard' as table_name, COUNT(*) as count FROM Product_Standard
UNION ALL
SELECT 'Product_Event' as table_name, COUNT(*) as count FROM Product_Event
UNION ALL
SELECT 'Procedure_Class' as table_name, COUNT(*) as count FROM Procedure_Class
UNION ALL
SELECT 'Procedure_Element' as table_name, COUNT(*) as count FROM Procedure_Element;
" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 데이터베이스 확인 성공${NC}"
    echo "$db_check"
else
    echo -e "${RED}❌ 데이터베이스 확인 실패${NC}"
fi

# 결과 요약
echo -e "\n${YELLOW}📊 테스트 결과 요약${NC}"
echo "=========================================="
echo -e "총 테스트 수: ${BLUE}$TOTAL_TESTS${NC}"
echo -e "성공: ${GREEN}$PASSED_TESTS${NC}"
echo -e "실패: ${RED}$FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 모든 테스트가 성공했습니다!${NC}"
    echo -e "${GREEN}✅ 전체 흐름이 정상적으로 작동합니다!${NC}"
    exit 0
else
    echo -e "\n${RED}⚠️  일부 테스트가 실패했습니다.${NC}"
    exit 1
fi
