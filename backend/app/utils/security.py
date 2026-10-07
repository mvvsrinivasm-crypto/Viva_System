from datetime import datetime, timedelta, timezone
import jwt
from flask import current_app


def create_jwt_token(user_id: int, role: str, name: str, email: str) -> str:
    secret = current_app.config["JWT_SECRET_KEY"]
    expire_hours = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES_HOURS", 24)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "user_id": int(user_id),
        "role": role,
        "name": name,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=expire_hours),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_jwt_token(token: str) -> dict:
    secret = current_app.config["JWT_SECRET_KEY"]
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid authentication token.")
