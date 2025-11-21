import os
import jwt
import bcrypt
from datetime import timedelta
from typing import Tuple, Dict, Any
from backend.fastapi_app.core.config import settings
from desktop_app.utils.utils import current_datetime_utc


def hash_password(password: str) -> str:
    """
    Hash the password using bcrypt and return a utf-8 string representation.
    """
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against the stored bcrypt hash.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False 
    
def create_jwt_token(subject: Dict[str, Any], minutes: int | None = None) -> str:
    """
    subject: dict of claims (e.g. {"employee_id": 1, "role": "admin"})
    """
    exp_minutes = minutes if minutes is not None else settings.JWT_EXP_MINUTES
    expire = current_datetime_utc() + timedelta(minutes=exp_minutes)
    payload = {
        **subject, 
        "exp": expire,
        "iat": current_datetime_utc()
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    # PyJWT returns str in mordern versions
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

def decode_jwt_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
