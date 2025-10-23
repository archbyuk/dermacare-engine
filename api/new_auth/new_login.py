import datetime
import os
import secrets
from datetime import timezone, datetime, timedelta
from fastapi import APIRouter, Depends, Response, HTTPException
import jwt
from jwt import PyJWTError
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.session import get_db
from pydantic import BaseModel
import bcrypt
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()

# 로그인 요청 및 응답 스키마
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    display_name: str
    organization_name: str
    group_name: str
    role: str

def verify_password(password: str, hash_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'), hash_password.encode('utf-8')
        )
    
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"비밀번호 확인 중 오류가 발생했습니다: {str(e)}")


# 액세스 토큰 생성
def generate_access_token(user_id: int, user_uuid: str, user_display_name: str, db:Session):
    
    # 토큰 생성을 위한 사용자 정보 조회
    token_payload_query = """
        SELECT
            org.uuid as organization_uuid, org.type as organization_type, org.name as organization_name,
            oum.created_at as date_joined_organization,
            g.group_name as group_name,
            r.role_name as role_name,
            p.resource, p.action, p.scope
        FROM 
            Organization_User_Mapping as oum
        JOIN
            Organization as org
                ON oum.organization_id = org.id
        JOIN
            OrgUser_Group_Role_Mapping as ougrm
                ON oum.id = ougrm.org_user_id
        JOIN
            `Group` as g
                ON ougrm.group_id = g.id
        JOIN
            `Role` as r
                ON ougrm.role_id = r.id
        JOIN
            Role_Permission_Mapping as rpm
                ON r.id = rpm.role_id
        JOIN
            Permission as p
                ON rpm.permission_id = p.id
        WHERE
            oum.user_id = :user_id
            AND
                org.is_active = 1
            AND
                g.is_active = 1
            AND
                r.is_active = 1
            AND
                p.is_active = 1
    """
    
    # 쿼리 실행
    query_result = db.execute(
        text(token_payload_query), {"user_id": user_id}
    )

    token_payload_rows = query_result.fetchall()

    # 조직별 데이터 그룹화
    user_organizations = {}

    for payload_row in token_payload_rows:
        organization_uuid = payload_row.organization_uuid
        
        # 조직 정보 초기화 및 필드 셋팅
        if organization_uuid not in user_organizations:
            user_organizations[organization_uuid] = {
                "organization_uuid": organization_uuid,
                "organization_name": payload_row.organization_name,
                "organization_type": payload_row.organization_type,
                "date_joined_organization": payload_row.date_joined_organization.isoformat() if payload_row.date_joined_organization else None,
                "user_groups": set(),
                "user_roles": set(),
                "user_permissions": set(),
            }

        
        # 그룹/역할/권한 추가
        user_organizations[organization_uuid]["user_groups"].add(payload_row.group_name)
        user_organizations[organization_uuid]["user_roles"].add(payload_row.role_name)
        user_permissions = f"{payload_row.resource}:{payload_row.action}:{payload_row.scope}"
        user_organizations[organization_uuid]["user_permissions"].add(user_permissions)
    
    # 리스트로 변환
    user_organizations_list = []
    
    for organization_uuid, organization_info in user_organizations.items():
        organization_info["user_groups"] = list(organization_info["user_groups"])
        organization_info["user_roles"] = list(organization_info["user_roles"])
        organization_info["user_permissions"] = list(organization_info["user_permissions"])
        
        user_organizations_list.append(organization_info)
    
    
    # JWT 페이로드 생성
    now = datetime.now(timezone.utc)
    expiration_time = now + timedelta(minutes=5)

    jwt_payload = {
        "iss": "MSO_API_AUTH_SERVER",
        "aud": "MSO_SERVICE_CLIENT",
        "sub": user_uuid,
        "display_name": user_display_name,
        "organizations": user_organizations_list,
        "current_org": user_organizations_list[0]["organization_uuid"] if user_organizations_list else None,
        "iat": int(now.timestamp()),
        "exp": int(expiration_time.timestamp())
    }
    
    # 환경변수에서 시크릿 키 가져오기
    secret_key = os.getenv("JWT_SECRET_KEY")
    
    if not secret_key:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY 환경변수가 없습니다.")

    try:
        token = jwt.encode(jwt_payload, secret_key, algorithm="HS256")
        
        return token
    
    except PyJWTError as e:
        raise HTTPException(status_code=500, detail=f"JWT 처리 중 오류 발생: {str(e)}")


# 리프레시 토큰 생성 (랜덤 문자열)
def generate_refresh_token(account_id: int, db: Session) -> str:
    refresh_token = secrets.token_urlsafe(32)
    refresh_expires = datetime.now(timezone.utc) + timedelta(days=7)

    refresh_token_query = """
        UPDATE 
            Account
        SET 
            refresh_token = :refresh_token, 
            token_expires_at = :refresh_expires, 
            last_login_at = :last_login_at
        WHERE 
            id = :account_id
    """
    # 리프레시 테스트 후 bcrypt 암호화 적용 예정

    db.execute(text(
        refresh_token_query), {
            "refresh_token": refresh_token, 
            "refresh_expires": refresh_expires, 
            "last_login_at": datetime.now(timezone.utc), 
            "account_id": account_id
        }
    )
    
    db.commit()
    
    return refresh_token



# 로그인 후 사용자 검증하고 JWT 토큰에 사용자 이름, 조직, 그룹, 역할, 권한 데이터 넣기
@router.post("/new_login", response_model=LoginResponse)
def new_login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    try:
        # 존재하는 사용자인지 확인
        user_verification = """
            SELECT
                a.id AS account_id,
                a.username,
                a.hash_password,
                a.is_active AS account_active,
                u.created_at AS user_created_date,
                u.id AS user_id,
                u.uuid AS user_uuid,
                u.display_name AS user_display_name,
                u.is_active AS user_active,
                org.name AS organization_name,
                g.group_name AS group_name,
                r.role_name AS role_name
            FROM 
                Account AS a
            JOIN 
                User AS u
                    ON a.id = u.account_id
            JOIN 
                Organization_User_Mapping AS oum
                    ON u.id = oum.user_id
            JOIN 
                Organization AS org
                    ON oum.organization_id = org.id
            JOIN 
                OrgUser_Group_Role_Mapping AS ougrm
                    ON oum.id = ougrm.org_user_id
            JOIN 
                `Group` AS g
                    ON ougrm.group_id = g.id
            JOIN 
                `Role` AS r
                    ON ougrm.role_id = r.id
            WHERE
                a.username = :username
                    AND a.is_active = 1
                    AND u.is_active = 1
                    AND org.is_active = 1
                    AND g.is_active = 1
                    AND r.is_active = 1
        """
        
        try:
            # user_verification 쿼리 실행(딕셔너리 형태로 반환)
            verification_result = db.execute(
                text(user_verification), {"username": request.username}
            )

            # 사용자 존재 여부 확인: 쿼리 실행 결과가 여기 들어감
            verified_user = verification_result.fetchone()
        
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=500, 
                detail=f"DB 에러가 발생했습니다.: {str(e)}"
            )

        if not verified_user:
            raise HTTPException(
                status_code=401, 
                detail="존재하지 않는 사용자입니다."
            )

        # 계정의 비밀번호 정보가 손상되었는지 확인
        if not verified_user.hash_password:
            raise HTTPException(
                status_code=500, 
                detail="계정의 비밀번호 정보가 손상되었습니다. 관리자에게 문의바랍니다."
            )

        # 로그인 입력 필드 검증 (사실 비밀번호만 확인하는데, 보안을 위해 아이디 or 비밀번호라고 표기)
        if not verify_password(request.password, verified_user.hash_password):
            raise HTTPException(
                status_code=401, 
                detail="아이디 또는 비밀번호가 잘못되었습니다."
            )

        
        # JWT 토큰 생성
        access_token = generate_access_token(
            user_id=verified_user.user_id, 
            user_uuid=verified_user.user_uuid,
            user_display_name=verified_user.user_display_name,
            db=db
        )
        refresh_token = generate_refresh_token(verified_user.account_id, db)

        # Set-Cookie 헤더 설정
        response.set_cookie(
            key="access_token",
            value=str(access_token),
            max_age=900,                # 15분
            httponly=True,              # XSS 방지
            secure=True,                # HTTPS 사용
            samesite="strict",          # 크로스 오리진 방지
            path="/"                    # 쿠키 경로(root: 전역 허용)
        )
        
        response.set_cookie(
            key="refresh_token",
            value=str(refresh_token),
            max_age=7*24*3600,          # 7일
            httponly=True,              # XSS 방지
            secure=True,                # HTTPS 사용
            samesite="strict",          # 크로스 오리진 방지
            path="/"                    # 쿠키 경로(root: 전역 허용)
        )

        return LoginResponse(
            success=True,
            message="로그인 성공",    # 성공 메시지 개선 필요: {user.team}의 {user.Username}님 환영합니다.
            display_name=verified_user.user_display_name,
            organization_name=verified_user.organization_name,
            group_name=verified_user.group_name,
            role=verified_user.role_name
        )
    
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))