#!/bin/bash

# Excel API 테스트 메뉴 스크립트

echo "🏥 DermaCare Excel API 테스트 도구"
echo "================================="
echo ""

# 서버 상태 확인
echo "🔍 서버 상태 확인 중..."
if curl -s http://localhost:9000/health > /dev/null; then
    echo "✅ 서버가 실행 중입니다 (http://localhost:9000)"
else
    echo "❌ 서버에 연결할 수 없습니다!"
    echo "   다음 명령어로 서버를 시작하세요:"
    echo "   cd /Users/jeongjin-ug/dermacare-engine/api"
    echo "   uvicorn main:app --reload --host 0.0.0.0 --port 9000"
    exit 1
fi

echo ""
echo "📋 테스트 메뉴를 선택하세요:"
echo "1) 단일 파일 업로드 테스트"
echo "2) 다중 파일 업로드 테스트"  
echo "3) 배치 업로드 테스트 (테이블 초기화)"
echo "4) API 문서 열기"
echo "5) 데이터베이스 현황 확인"
echo "0) 종료"
echo ""

read -p "선택 (0-5): " choice

case $choice in
    1)
        echo ""
        echo "📁 단일 파일 업로드 테스트"
        echo "사용 가능한 파일들:"
        ls -1 /Users/jeongjin-ug/Downloads/DataTable/*.xlsx 2>/dev/null | sed 's|.*/||' | nl -v0
        echo ""
        read -p "파일명을 입력하세요 (기본값: Enum.xlsx): " filename
        ./test_single_upload.sh "${filename:-Enum.xlsx}"
        ;;
    2)
        echo ""
        echo "📁 다중 파일 업로드 테스트"
        ./test_multiple_upload.sh
        ;;
    3)
        echo ""
        echo "🗑️  배치 업로드 테스트 (테이블 초기화)"
        echo "⚠️  주의: 모든 데이터가 삭제됩니다!"
        ./test_batch_upload.sh true
        ;;
    4)
        echo ""
        echo "🌐 API 문서를 브라우저에서 엽니다..."
        if command -v open >/dev/null 2>&1; then
            open "http://localhost:9000/docs"
        else
            echo "브라우저에서 다음 주소를 열어주세요:"
            echo "http://localhost:9000/docs"
        fi
        ;;
    5)
        echo ""
        echo "📊 데이터베이스 현황 확인"
        DB_PASSWORD=$(grep '^DB_PASSWORD=' .env | cut -d= -f2-)
        DB_NAME=$(grep '^DB_NAME=' .env | cut -d= -f2-)
        docker-compose exec -T db sh -c "mysql -uroot -p$DB_PASSWORD -e \"USE $DB_NAME; 
        SELECT 'Enum' as table_name, COUNT(*) as count FROM Enum
        UNION ALL SELECT 'Consumables', COUNT(*) FROM Consumables
        UNION ALL SELECT 'Global', COUNT(*) FROM Global  
        UNION ALL SELECT 'Procedure_Element', COUNT(*) FROM Procedure_Element
        UNION ALL SELECT 'Procedure_Bundle', COUNT(*) FROM Procedure_Bundle
        UNION ALL SELECT 'Procedure_Sequence', COUNT(*) FROM Procedure_Sequence
        UNION ALL SELECT 'Procedure_Class', COUNT(*) FROM Procedure_Class
        UNION ALL SELECT 'Info_Standard', COUNT(*) FROM Info_Standard
        UNION ALL SELECT 'Info_Event', COUNT(*) FROM Info_Event
        UNION ALL SELECT 'Product_Standard', COUNT(*) FROM Product_Standard
        UNION ALL SELECT 'Product_Event', COUNT(*) FROM Product_Event;\"" | cat
        ;;
    0)
        echo "👋 테스트 도구를 종료합니다."
        exit 0
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac
