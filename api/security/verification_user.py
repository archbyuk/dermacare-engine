from fastapi import HTTPException, status, Request
import jwt
import os
from datetime import datetime, timezone
import dotenv

dotenv.load_dotenv()

# 모듈 레벨 싱글톤 상태
_secret_key = None

# JWT 토큰 검증
def verification_jwt(request: Request):
    global _secret_key
    
    try:
        # 1. 토큰 추출
        target_token = request.cookies.get("access_token")
        
        if not target_token:
            raise HTTPException(
                status_code=401, 
                detail="사용자 인증 토큰이 없습니다. 로그인이 필요합니다."
            )
        
        # 2. 시크릿 키는 한 번만 로드
        if _secret_key is None:
            _secret_key = os.getenv("JWT_SECRET_KEY")
            
            if not _secret_key:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="JWT_SECRET_KEY 환경변수가 설정되지 않았습니다."
                )
        
        # 3. JWT 디코딩 및 검증
        payload = jwt.decode(
            target_token, 
            _secret_key, 
            algorithms=["HS256"],
            audience="MSO_SERVICE_CLIENT"
        )
        
        # 4. 토큰 만료 확인
        exp = payload.get("exp")
        current_time = datetime.now(timezone.utc).timestamp()
        
        if exp and current_time > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰이 만료되었습니다."
            )
        
        # 5. 사용자 정보 추출
        user_uuid = payload.get("sub")
        display_name = payload.get("display_name")
        organizations = payload.get("organizations", [])
        
        if not user_uuid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다."
            )
        
        # 6. 권한 추출 (인라인으로 처리)
        all_permissions = []
        for org in organizations:
            all_permissions.extend(org.get("user_permissions", []))
        
        permissions = list(set(all_permissions))  # 중복 제거
        
        # 7. 사용자 정보 반환
        user_info = {
            "user_uuid": user_uuid,
            "display_name": display_name,
            "organizations": organizations,
            "permissions": permissions
        }
        
        # 디버깅 로그: 사용자 인증 완료
        print(f"[AUTH] 사용자 인증 완료 - UUID: {user_uuid}, 이름: {display_name}")
        print(f"[AUTH] 소속 조직 UUID: {[org['organization_uuid'] for org in organizations]}")
        print(f"[AUTH] 소속 조직: {[org['organization_name'] for org in organizations]}")
        print(f"[AUTH] 보유 권한: {permissions}")
        
        return user_info
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="토큰이 만료되었습니다."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="유효하지 않은 토큰입니다."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="JWT 토큰 검증 실패"
        )