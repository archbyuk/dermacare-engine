#!/usr/bin/env python3
"""
    API를 통한 더미 데이터 생성 스크립트
"""

import requests
import random
from datetime import datetime, date, time, timedelta
import json

# API 기본 URL
API_BASE_URL = "http://localhost:9000/consultations/create"

# 샘플 데이터
customer_names = [
    "김민수", "이영희", "박철수", "최지영", "정수진", "한동훈", "윤서연", "강민호",
    "조현우", "임소영", "오준석", "신예린", "배지훈", "송하늘", "권민정", "황태현",
    "서지원", "노승현", "문소정", "유재석", "김태희", "이민호", "박보영", "최우식",
    "정유미", "한소희", "윤아", "강동원", "조인성", "임수정", "오정세", "신민아",
    "배두나", "송강", "권상우", "황정음", "서강준", "노지훈", "문채원", "유아인"
]

inflow_paths = [
    "인스타그램", "네이버", "페이스북", "유튜브", "지인소개", "병원직접방문", 
    "구글검색", "카카오톡", "블로그", "온라인광고"
]

consultation_types = [
    "시술상담", "가격문의", "후기상담", "상담문의", "시술예약", "결제문의",
    "시술후상담", "재방문상담", "긴급상담", "전화상담"
]

concern_types = [
    "주름", "탄력", "색소침착", "모공", "흉터", "여드름", "기미", "주근깨",
    "눈가주름", "이마주름", "볼처짐", "턱선", "목주름", "손등주름"
]

purchased_items = [
    "보톡스", "필러", "레이저", "리프팅", "스킨케어", "마사지", "팩", "세럼"
]

membership_types = [
    "골드맴버십", "실버맴버십", "VIP맴버십", "일반맴버십", "프리미엄맴버십"
]

payment_types = [
    "카드결제", "현금결제", "계좌이체", "무통장입금", "할부결제"
]

consultation_contents = [
    "리프팅 시술에 대해 문의드립니다.",
    "보톡스 시술 후 관리 방법을 알고 싶습니다.",
    "필러 시술의 효과와 지속기간에 대해 상담받고 싶습니다.",
    "레이저 시술의 부작용과 주의사항을 문의합니다.",
    "스킨케어 프로그램에 대해 자세히 알고 싶습니다.",
    "여드름 치료 방법과 예상 비용을 문의합니다.",
    "기미 제거 시술의 효과와 과정을 상담받고 싶습니다.",
    "모공 축소 시술에 대한 정보를 요청합니다.",
    "눈가 주름 개선을 위한 시술 옵션을 문의합니다.",
    "전체적인 안면 관리 프로그램을 상담받고 싶습니다."
]

def generate_dummy_consultation(index):
    """더미 상담 데이터 생성"""
    
    # 랜덤 날짜 생성 (최근 6개월)
    start_date = date.today() - timedelta(days=random.randint(0, 180))
    
    # 랜덤 시간 생성 (09:00 ~ 18:00)
    start_hour = random.randint(9, 17)
    start_minute = random.choice([0, 15, 30, 45])
    start_time_obj = time(start_hour, start_minute)
    
    # 상담 시간 (15분 ~ 120분)
    duration_minutes = random.choice([15, 30, 45, 60, 90, 120])
    end_time_obj = time(
        (start_hour * 60 + start_minute + duration_minutes) // 60 % 24,
        (start_hour * 60 + start_minute + duration_minutes) % 60
    )
    
    # 랜덤 데이터 생성
    customer_name = random.choice(customer_names)
    chart_number = random.randint(20000, 99999)
    
    # 유입경로 (1-3개 랜덤 선택)
    selected_inflow = random.sample(inflow_paths, random.randint(1, 3))
    inflow_path = ",".join(selected_inflow)
    
    # 상담유형 (1-3개 랜덤 선택)
    selected_types = random.sample(consultation_types, random.randint(1, 3))
    consultation_type = ",".join(selected_types)
    
    # 고민유형 (1-4개 랜덤 선택)
    selected_concerns = random.sample(concern_types, random.randint(1, 4))
    concern_type = ",".join(selected_concerns)
    
    # 구매상품 (50% 확률로 선택)
    purchased_items_str = None
    if random.random() < 0.5:
        selected_items = random.sample(purchased_items, random.randint(1, 3))
        purchased_items_str = ",".join(selected_items)
    
    # 맴버십 (30% 확률로 선택)
    has_membership = None
    if random.random() < 0.3:
        has_membership = random.choice(membership_types)
    
    # 결제타입 (40% 확률로 선택)
    payment_type = None
    if random.random() < 0.4:
        payment_type = random.choice(payment_types)
    
    # 할인율 (20% 확률로 선택)
    discount_rate = None
    if random.random() < 0.2:
        discount_rate = round(random.uniform(0, 10), 1)
    
    # 결제액 (30% 확률로 선택)
    total_payment = None
    if random.random() < 0.3:
        total_payment = random.randint(100000, 5000000)
    
    # 상담 내용
    consultation_content = random.choice(consultation_contents)
    
    return {
        "consultation_date": start_date.strftime("%Y-%m-%d"),
        "start_time": start_time_obj.strftime("%H:%M:%S"),
        "end_time": end_time_obj.strftime("%H:%M:%S"),
        "customer_name": customer_name,
        "chart_number": chart_number,
        "inflow_path": inflow_path,
        "consultation_type": consultation_type,
        "goal_treatment": random.choice([True, False]),
        "concern_type": concern_type,
        "is_upselling": random.choice([True, False]),
        "consultation_content": consultation_content,
        "purchased_items": purchased_items_str,
        "has_membership": has_membership,
        "payment_type": payment_type,
        "discount_rate": discount_rate,
        "total_payment": total_payment
    }

def create_dummy_consultations(count=300):
    """더미 상담 데이터 생성"""
    
    print(f"🚀 {count}개의 더미 상담 데이터 생성 시작...")
    
    success_count = 0
    error_count = 0
    
    for i in range(count):
        try:
            # 더미 데이터 생성
            consultation_data = generate_dummy_consultation(i)
            
            # API 호출
            response = requests.post(
                API_BASE_URL,
                headers={"Content-Type": "application/json"},
                json=consultation_data,
                timeout=10
            )
            
            if response.status_code == 200:
                success_count += 1
                if (i + 1) % 50 == 0:
                    print(f"📊 {i + 1}개 생성 완료... (성공: {success_count}, 실패: {error_count})")
            else:
                error_count += 1
                print(f"❌ {i + 1}번째 요청 실패: {response.status_code}")
                
        except Exception as e:
            error_count += 1
            print(f"❌ {i + 1}번째 요청 오류: {str(e)}")
    
    print(f"✅ 더미 데이터 생성 완료!")
    print(f"📊 성공: {success_count}개, 실패: {error_count}개")

if __name__ == "__main__":
    create_dummy_consultations(300)
