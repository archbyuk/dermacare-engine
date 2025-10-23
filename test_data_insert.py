# test_data_insert.py
import os
import sys
import bcrypt
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
import uuid
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 데이터베이스 URL 설정
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")

# 환경변수 검증
if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    print("❌ 환경변수가 설정되지 않았습니다.")
    print("다음 환경변수를 설정해주세요:")
    print("- DB_USER: 데이터베이스 사용자명")
    print("- DB_PASSWORD: 데이터베이스 비밀번호")
    print("- DB_NAME: 데이터베이스 이름")
    print("- DB_HOST: 데이터베이스 호스트 (기본값: localhost)")
    print("- DB_PORT: 데이터베이스 포트 (기본값: 3306)")
    sys.exit(1)

# 데이터베이스 URL 설정(sync)
SYNC_DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

print(f"🔗 데이터베이스 연결 시도: {DB_HOST}:{DB_PORT}/{DB_NAME}")

# SQLAlchemy 엔진 생성
try:
    engine = create_engine(
        SYNC_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,  # 연결 상태 확인
        pool_recycle=3600,   # 연결 재사용 시간 (1시간)
    )
    print("✅ 데이터베이스 엔진 생성 완료")
except Exception as e:
    print(f"❌ 데이터베이스 엔진 생성 실패: {e}")
    sys.exit(1)

def insert_test_data():
    """테스트 데이터 삽입 함수"""
    print("🚀 테스트 데이터 삽입 시작...")
    
    try:
        with engine.begin() as conn:
            print("📊 데이터베이스 연결 성공")
            
            # 기존 테스트 데이터 삭제
            print("🗑️ 기존 테스트 데이터 삭제 중...")
            conn.execute(text("DELETE FROM Role_Permission_Mapping WHERE role_id IN (SELECT id FROM `Role` WHERE role_name = 'Admin')"))
            conn.execute(text("DELETE FROM OrgUser_Group_Role_Mapping WHERE org_user_id IN (SELECT id FROM Organization_User_Mapping WHERE user_id IN (SELECT id FROM User WHERE display_name = '테스트 사용자'))"))
            conn.execute(text("DELETE FROM Permission WHERE description LIKE '%상담%' OR description LIKE '%급여%'"))
            conn.execute(text("DELETE FROM `Role` WHERE role_name = 'Admin'"))
            conn.execute(text("DELETE FROM `Group` WHERE group_name = '상담팀'"))
            conn.execute(text("DELETE FROM Organization_User_Mapping WHERE user_id IN (SELECT id FROM User WHERE display_name = '테스트 사용자')"))
            conn.execute(text("DELETE FROM User WHERE display_name = '테스트 사용자'"))
            conn.execute(text("DELETE FROM Account WHERE username = 'testuser'"))
            conn.execute(text("DELETE FROM Organization WHERE name IN ('Theranova', 'FaceFilter', 'Suwon')"))
            print("✅ 기존 테스트 데이터 삭제 완료")
            
            # 1. Account 테이블에 테스트 사용자 추가
            test_password = "test123"
            hashed_password = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
            account_query = """
                INSERT INTO Account (uuid, is_active, username, hash_password, refresh_token, token_expires_at, last_login_at, created_at, updated_at)
                VALUES (:uuid, 1, :username, :hash_password, NULL, NULL, NULL, :created_at, :updated_at)
            """
            
            account_uuid = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            result = conn.execute(text(account_query), {
                'uuid': account_uuid,
                'username': "testuser",
                'hash_password': hashed_password,
                'created_at': now,
                'updated_at': now
            })
            account_id = result.lastrowid
            print(f"✅ Account 생성 완료 (ID: {account_id})")
        
            # 2. User 테이블에 사용자 정보 추가
            user_uuid = str(uuid.uuid4())
            user_query = """
                INSERT INTO User (uuid, account_id, is_active, display_name, created_at, updated_at)
                VALUES (:uuid, :account_id, 1, :display_name, :created_at, :updated_at)
            """
            
            result = conn.execute(text(user_query), {
                'uuid': user_uuid,
                'account_id': account_id,
                'display_name': "테스트 사용자",
                'created_at': now,
                'updated_at': now
            })
            user_id = result.lastrowid
            print(f"✅ User 생성 완료 (ID: {user_id})")
        
            # 3. Organization 테이블에 조직 정보 추가 (MSO → Hospital → Branch 계층 구조)
            
            # 3-1. MSO (최상위)
            mso_uuid = str(uuid.uuid4())
            mso_query = """
                INSERT INTO Organization (uuid, parents_id, type, is_active, name, description, address, phone, domain, logo, created_at, updated_at)
                VALUES (:uuid, NULL, 'MSO', 1, :name, :description, NULL, NULL, NULL, NULL, :created_at, :updated_at)
            """
            
            result = conn.execute(text(mso_query), {
                'uuid': mso_uuid,
                'name': "Theranova",
                'description': "MSO 본사",
                'created_at': now,
                'updated_at': now
            })
            mso_id = result.lastrowid
            print(f"✅ MSO Organization 생성 완료 (ID: {mso_id})")
            
            # 3-2. Hospital (MSO 하위)
            hospital_uuid = str(uuid.uuid4())
            hospital_query = """
                INSERT INTO Organization (uuid, parents_id, type, is_active, name, description, address, phone, domain, logo, created_at, updated_at)
                VALUES (:uuid, :parents_id, 'Hospital', 1, :name, :description, NULL, NULL, NULL, NULL, :created_at, :updated_at)
            """
            
            result = conn.execute(text(hospital_query), {
                'uuid': hospital_uuid,
                'parents_id': mso_id,
                'name': "FaceFilter",
                'description': "FaceFilter 병원",
                'created_at': now,
                'updated_at': now
            })
            hospital_id = result.lastrowid
            print(f"✅ Hospital Organization 생성 완료 (ID: {hospital_id})")
            
            # 3-3. Branch (Hospital 하위)
            branch_uuid = str(uuid.uuid4())
            branch_query = """
                INSERT INTO Organization (uuid, parents_id, type, is_active, name, description, address, phone, domain, logo, created_at, updated_at)
                VALUES (:uuid, :parents_id, 'Branch', 1, :name, :description, NULL, NULL, NULL, NULL, :created_at, :updated_at)
            """
            
            result = conn.execute(text(branch_query), {
                'uuid': branch_uuid,
                'parents_id': hospital_id,
                'name': "Suwon",
                'description': "Suwon 지점",
                'created_at': now,
                'updated_at': now
            })
            branch_id = result.lastrowid
            print(f"✅ Branch Organization 생성 완료 (ID: {branch_id})")
            
            # 사용자는 Branch에 소속
            organization_id = branch_id
        
            # 4. Organization_User_Mapping 테이블에 관계 설정
            oum_uuid = str(uuid.uuid4())
            oum_query = """
                INSERT INTO Organization_User_Mapping (uuid, user_id, organization_id, created_at, updated_at)
                VALUES (:uuid, :user_id, :organization_id, :created_at, :updated_at)
            """
            
            result = conn.execute(text(oum_query), {
                'uuid': oum_uuid,
                'user_id': user_id,
                'organization_id': organization_id,
                'created_at': now,
                'updated_at': now
            })
            oum_id = result.lastrowid
            print(f"✅ Organization_User_Mapping 생성 완료 (ID: {oum_id})")
            
            # 5. Group 테이블에 그룹 정보 추가
            group_uuid = str(uuid.uuid4())
            group_query = """
                INSERT INTO `Group` (uuid, organization_id, is_active, group_name, group_description, created_at, updated_at)
                VALUES (:uuid, :organization_id, 1, :group_name, :group_description, :created_at, :updated_at)
            """
            
            result = conn.execute(text(group_query), {
                'uuid': group_uuid,
                'organization_id': organization_id,
                'group_name': "상담팀",
                'group_description': "테스트용 상담팀",
                'created_at': now,
                'updated_at': now
            })
            group_id = result.lastrowid
            print(f"✅ Group 생성 완료 (ID: {group_id})")
            
            # 6. Role 테이블에 역할 정보 추가
            role_uuid = str(uuid.uuid4())
            role_query = """
                INSERT INTO `Role` (uuid, group_id, is_active, role_name, role_description, created_at, updated_at)
                VALUES (:uuid, :group_id, 1, :role_name, :role_description, :created_at, :updated_at)
            """
            
            result = conn.execute(text(role_query), {
                'uuid': role_uuid,
                'group_id': group_id,
                'role_name': "Admin",
                'role_description': "테스트용 관리자",
                'created_at': now,
                'updated_at': now
            })
            role_id = result.lastrowid
            print(f"✅ Role 생성 완료 (ID: {role_id})")
            
            # 7. Permission 테이블에 권한 정보 추가
            permission_query = """
                INSERT INTO Permission (resource, action, scope, description, created_at, updated_at)
                VALUES (:resource, :action, :scope, :description, :created_at, :updated_at)
            """
            
            permissions = [
                {"resource": "consultation", "action": "read", "scope": "all", "description": "상담 조회 권한"},
                {"resource": "consultation", "action": "create", "scope": "group", "description": "상담 생성 권한"},
                {"resource": "salary", "action": "read", "scope": "own", "description": "급여 조회 권한"}
            ]
            
            permission_ids = []
            for perm in permissions:
                params = {
                    'resource': perm["resource"],
                    'action': perm["action"],
                    'scope': perm["scope"],
                    'description': perm["description"],
                    'created_at': now,
                    'updated_at': now
                }
                result = conn.execute(text(permission_query), params)
                permission_ids.append(result.lastrowid)
            print(f"✅ Permission 생성 완료 ({len(permission_ids)}개)")
            
            # 8. OrgUser_Group_Role_Mapping 테이블에 관계 설정
            ogrm_query = """
                INSERT INTO OrgUser_Group_Role_Mapping (group_id, role_id, org_user_id, created_at, updated_at)
                VALUES (:group_id, :role_id, :org_user_id, :created_at, :updated_at)
            """
            
            conn.execute(text(ogrm_query), {
                'group_id': group_id,
                'role_id': role_id,
                'org_user_id': oum_id,
                'created_at': now,
                'updated_at': now
            })
            print("✅ OrgUser_Group_Role_Mapping 생성 완료")
            
            # 9. Role_Permission_Mapping 테이블에 관계 설정
            rpm_query = """
                INSERT INTO Role_Permission_Mapping (role_id, permission_id, created_at)
                VALUES (:role_id, :permission_id, :created_at)
            """
            
            for pid in permission_ids:
                conn.execute(text(rpm_query), {
                    'role_id': role_id,
                    'permission_id': pid,
                    'created_at': now
                })
            print("✅ Role_Permission_Mapping 생성 완료")
            
            print("🎉 테스트 데이터가 성공적으로 삽입되었습니다!")
            
    except Exception as e:
        print(f"❌ 테스트 데이터 삽입 실패: {e}")
        raise

if __name__ == "__main__":
    insert_test_data()