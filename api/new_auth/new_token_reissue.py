from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from db.session import get_db
from pydantic import BaseModel
from datetime import datetime, timezone
import jwt
import os
from jwt import PyJWTError

router = APIRouter()

# 요청/응답 스키마
class RefreshRequest(BaseModel):
    refresh_token: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    user_id: int
    user_uuid: str
    username: str
    display_name: str
    organizations: list

# 리프레시 토큰 검증 및 사용자 정보 조회
def verify_refresh_token(refresh_token: str, db: Session):
    """
    리프레시 토큰을 검증하고 사용자 정보를 반환합니다.
    """
    try:
        # 리프레시 토큰으로 사용자 정보 조회
        refresh_verification = """
            SELECT
                a.id AS account_id,
                a.username,
                a.is_active AS account_active,
                u.id AS user_id,
                u.uuid AS user_uuid,
                u.display_name AS user_display_name,
                u.is_active AS user_active,
                a.refresh_token,
                a.token_expires_at
            FROM 
                Account AS a
            JOIN 
                User AS u
                    ON a.id = u.account_id
            WHERE
                a.refresh_token = :refresh_token
                AND a.is_active = 1
                AND u.is_active = 1
                AND a.token_expires_at > :current_time
        """
        
        current_time = datetime.now(timezone.utc)
        result = db.execute(text(refresh_verification), {
            "refresh_token": refresh_token,
            "current_time": current_time
        })
        
        user_info = result.fetchone()
        
        if not user_info:
            raise HTTPException(
                status_code=401, 
                detail="유효하지 않은 리프레시 토큰입니다."
            )
        
        return user_info
        
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"DB 에러가 발생했습니다: {str(e)}"
        )

# 새로운 액세스 토큰 생성 (기존 generate_access_token 함수 재사용)
def generate_new_access_token(user_id: int, user_uuid: str, user_display_name: str, db: Session) -> str:
    """
    사용자 정보를 기반으로 새로운 액세스 토큰을 생성합니다.
    """
    # 토큰 페이로드 쿼리 (기존과 동일)
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
    
    try:
        query_result = db.execute(text(token_payload_query), {"user_id": user_id})
        token_payload_rows = query_result.fetchall()
        
        if not token_payload_rows:
            raise HTTPException(
                status_code=500, 
                detail="사용자의 조직 정보를 찾을 수 없습니다."
            )
        
        # 조직별 정보 그룹화
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
        from datetime import timedelta
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
            
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"DB 에러가 발생했습니다: {str(e)}"
        )

@router.post("/refresh", response_model=LoginResponse)
def refresh_token(
    request: RefreshRequest, 
    response: Response, 
    db: Session = Depends(get_db)
):
    """
    리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급합니다.
    """
    try:
        print("[DEBUG][refresh request]", request)
        # 리프레시 토큰 검증 및 사용자 정보 조회
        user_info = verify_refresh_token(request.refresh_token, db)
        
        # 새로운 액세스 토큰 생성
        access_token = generate_new_access_token(
            user_id=user_info.user_id,
            user_uuid=user_info.user_uuid,
            user_display_name=user_info.user_display_name,
            db=db
        )
        
        # 새로운 액세스 토큰을 쿠키에 설정
        response.set_cookie(
            key="access_token",
            value=str(access_token),
            max_age=900,                # 15분
            httponly=True,              # XSS 방지
            secure=True,                # HTTPS 사용
            samesite="strict",          # 크로스 오리진 방지
            path="/"                    # 쿠키 경로(root: 전역 허용)
        )
        
        return LoginResponse(
            success=True,
            message="토큰 갱신 성공",
            user_id=user_info.user_id,
            user_uuid=user_info.user_uuid,
            username=user_info.username,
            display_name=user_info.user_display_name,
            organizations=[]  # 필요시 조직 정보도 반환 가능
        )
        
    except HTTPException:
        # HTTPException은 그대로 재발생
        raise
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"토큰 갱신 중 오류가 발생했습니다: {str(e)}"
        )
