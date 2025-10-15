"""
    [ 인증 서비스 ]

    인증 관련 비즈니스 로직 처리
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from db.models.users import Users
from auth.utils.token_utils import generate_access_token, generate_refresh_token


# 로그인 처리: 사용자 인증 + 토큰 생성 + DB 저장
# return: (user, access_token, refresh_token)
def process_login(db: Session, username: str, password: str) -> tuple[Users, str, str]:
    
    # 사용자 조회
    user = db.query(Users).filter(
        Users.Username == username
    ).first()
    
    if not user:
        raise ValueError("사용자를 찾을 수 없습니다")
    
    # 비밀번호 확인 (간단한 문자열 비교): 추후 비밀번호 저장 방식 변경 필요 -> 비밀번호 암호화
    if user.Password != password:
        raise ValueError("비밀번호가 일치하지 않습니다")
    
    # JWT 토큰 생성
    access_token = generate_access_token(user.ID, user.Username, user.Role)
    refresh_token = generate_refresh_token()
    
    # 리프레시 토큰 만료 시간 설정 (7일)
    refresh_expires = datetime.now(timezone.utc) + timedelta(days=7)
    
    # 데이터베이스에 토큰 정보 저장
    user.Refresh_Token = refresh_token
    user.Token_Expires_At = refresh_expires
    user.Last_Login_At = datetime.now(timezone.utc)
    
    db.commit()
    
    return user, access_token, refresh_token


# 로그아웃 처리: 리프레시 토큰 무효화
# return: None
def process_logout(db: Session, refresh_token: str) -> None:
    
    # 리프레시 토큰으로 사용자 조회
    user = db.query(Users).filter(
        Users.Refresh_Token == refresh_token
    ).first()
    
    if user:
        # 토큰 정보 초기화
        user.Refresh_Token = None
        user.Token_Expires_At = None
        
        db.commit()


# 토큰 갱신 처리: 리프레시 토큰 검증 + 새 액세스 토큰 생성
# return: (user, access_token)
def process_token_refresh(db: Session, refresh_token: str) -> tuple[Users, str]:
    
    # 리프레시 토큰으로 사용자 조회 (만료되지 않은 토큰만)
    user = db.query(Users).filter(
        Users.Refresh_Token == refresh_token,
        Users.Token_Expires_At > datetime.now(timezone.utc)
    ).first()
    
    if not user:
        raise ValueError("유효하지 않은 리프레시 토큰입니다")
    
    # 새로운 액세스 토큰 생성
    access_token = generate_access_token(user.ID, user.Username, user.Role)
    
    return user, access_token

