from datetime import datetime, timedelta, timezone
import jwt
import secrets
import os

# 액세스 토큰 생성
def generate_access_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "iat": datetime.now(timezone.utc)
    }
    # 환경변수에서 시크릿 키 가져오기
    secret_key = os.getenv("JWT_SECRET_KEY", "dermacare_secret_key_2024")
    return jwt.encode(payload, secret_key, algorithm="HS256")


# 리프레시 토큰 생성 (랜덤 문자열)
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)