import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException
from config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD

_serializer = URLSafeTimedSerializer(SECRET_KEY)
SESSION_COOKIE = "ilgregario_session"
MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_session_token(user_id: str, is_admin: bool, username: str = "") -> str:
    return _serializer.dumps({"user_id": user_id, "is_admin": is_admin, "username": username})


def decode_session_token(token: str) -> dict | None:
    try:
        return _serializer.loads(token, max_age=MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_session(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return decode_session_token(token)


def require_session(request: Request) -> dict:
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return session


def require_admin(request: Request) -> dict:
    session = require_session(request)
    if not session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return session


def check_admin_credentials(username: str, password: str) -> bool:
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD
