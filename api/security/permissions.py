"""
권한 관리 모듈

데코레이터를 사용한 권한 검사 시스템
"""

from functools import wraps
from fastapi import HTTPException, Request

def require_permission(permission: str):
    """
    권한 검사 데코레이터
    
    Args:
        permission: 필요한 권한 (예: "products_list:read:all")
    
    Usage:
        @router.get("/products")
        @require_permission("products_list:read:all")
        def get_products(request: Request):
            # 권한 검사 완료, 비즈니스 로직만
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request: Request, *args, **kwargs):
            # 미들웨어에서 검증된 사용자 정보 가져오기
            user_info = request.state.user
            
            # 권한 검사
            if permission not in user_info.get("permissions", []):
                raise HTTPException(
                    status_code=403,
                    detail=f"권한이 없습니다. 필요한 권한: {permission}"
                )
            
            # 권한 검사 통과 시 원래 함수 실행
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_role(role: str):
    """
    역할 검사 데코레이터
    
    Args:
        role: 필요한 역할 (예: "Admin", "Manager")
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request: Request, *args, **kwargs):
            user_info = request.state.user
            
            # 모든 조직에서 역할 확인
            has_role = False
            for org in user_info.get("organizations", []):
                if role in org.get("user_roles", []):
                    has_role = True
                    break
            
            if not has_role:
                raise HTTPException(
                    status_code=403,
                    detail=f"권한이 없습니다. 필요한 역할: {role}"
                )
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_group(group: str):
    """
    그룹 검사 데코레이터
    
    Args:
        group: 필요한 그룹 (예: "상담팀", "관리팀")
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request: Request, *args, **kwargs):
            user_info = request.state.user
            
            # 모든 조직에서 그룹 확인
            has_group = False
            for org in user_info.get("organizations", []):
                if group in org.get("user_groups", []):
                    has_group = True
                    break
            
            if not has_group:
                raise HTTPException(
                    status_code=403,
                    detail=f"권한이 없습니다. 필요한 그룹: {group}"
                )
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
