from fastapi import APIRouter, Request
import os
import jwt

router = APIRouter()

@router.get("/debug/echo")
async def echo_auth_context(request: Request, raw: bool = False):
    """
    쿠키와 Authorization 헤더를 에코하여
    클라이언트-서버 간 쿠키 전송/수신을 점검하기 위한 더미 엔드포인트.
    절대 민감 정보(평문 토큰 등)를 영구 저장하지 않음.
    """
    cookies = dict(request.cookies)
    # 보안상 실제 토큰 전체를 그대로 반환하지 않고 길이/마스킹 정보만 제공
    masked_cookies = {
        k: (f"len={len(v)}" if isinstance(v, str) else "") for k, v in cookies.items()
    }

    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    masked_auth = None
    if auth_header:
        # 예: "Bearer abcdef..." 형태 길이만 표시
        masked_auth = f"len={len(auth_header)}"

    # dict 스타일 직접 접근 테스트
    access_token_direct = None
    access_token_len = 0
    try:
        access_token_direct = request.cookies['access_token']
        access_token_len = len(access_token_direct) if isinstance(access_token_direct, str) else 0
    except KeyError:
        access_token_direct = None

    # --- 요청 바디 ---
    try:
        body_bytes = await request.body()
        body_len = len(body_bytes) if body_bytes else 0
    except Exception:
        body_bytes = b""
        body_len = 0

    # --- JWT 디코딩 (쿠키 access_token 우선, 없으면 Authorization) ---
    jwt_payload = None
    jwt_error = None
    token_for_decode = access_token_direct or (
        auth_header.split(" ", 1)[1] if (auth_header and auth_header.lower().startswith("bearer ")) else None
    )
    if token_for_decode:
        try:
            secret_key = os.getenv("JWT_SECRET_KEY", "dermacare_secret_key_2024")
            jwt_payload = jwt.decode(token_for_decode, secret_key, algorithms=["HS256"])
        except Exception as e:
            jwt_error = str(e)

    # --- 콘솔 출력 (민감정보 마스킹) ---
    try:
        client_host = getattr(request.client, "host", None)
        client_port = getattr(request.client, "port", None)
        path = request.url.path
        method = request.method
        # 헤더 키와 길이만 출력
        masked_headers = {k: (f"len={len(v)}" if isinstance(v, str) else "") for k, v in request.headers.items()}
        print("[DEBUG][echo]", {
            "client": f"{client_host}:{client_port}",
            "method": method,
            "path": path,
            "headers": masked_headers,
            "cookies": masked_cookies,
            "access_token_direct_present": bool(access_token_direct),
            "access_token_direct_len": access_token_len,
            "body_len": body_len,
            "jwt_present": bool(token_for_decode),
            "jwt_decoded": bool(jwt_payload),
        })
    except Exception as _:
        # 로깅 실패는 무시
        pass

    if raw:
        # 로컬 디버깅용: 원문 노출(주의)
        return {
            "ok": True,
            "client": {
                "host": getattr(request.client, "host", None),
                "port": getattr(request.client, "port", None),
            },
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers_raw": dict(request.headers),
            "cookies_raw": cookies,
            "authorization_raw": auth_header,
            "body_len": body_len,
            "body_preview": body_bytes[:512].decode(errors="ignore") if body_bytes else "",
            "jwt_payload": jwt_payload,
            "jwt_error": jwt_error,
        }
    else:
        # 마스킹 모드
        masked_payload = None
        if isinstance(jwt_payload, dict):
            masked_payload = {k: (v if k in {"user_id", "username", "role", "exp", "iat"} else "hidden") for k, v in jwt_payload.items()}
        return {
            "ok": True,
            "cookies_present": list(cookies.keys()),
            "cookies_masked": masked_cookies,
            "authorization_masked": masked_auth,
            "access_token_direct_present": bool(access_token_direct),
            "access_token_direct_len": access_token_len,
            "user_agent": request.headers.get("user-agent"),
            "origin": request.headers.get("origin"),
            "body_len": body_len,
            "jwt_decoded": bool(jwt_payload),
            "jwt_payload_masked": masked_payload,
            "jwt_error": jwt_error,
        }


