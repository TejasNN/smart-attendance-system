# backend/fastapi_app/services/token_service.py
import secrets
import bcrypt
from typing import Tuple

# Token generation / hashing helpers used by provisioning flow

def generate_token(length_bytes: int = 32) -> str:
    """
    Generate a URL-safe, high-entropy token.
    length_bytes controls entropy; token_urlsafe will produce a string longer than length_bytes.
    """
    return secrets.token_urlsafe(length_bytes)

def hash_token_bcrypt(token: str) -> str:
    """
    Hash the token using bcrypt and return a utf-8 string representation.
    """
    hashed = bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_token_bcrypt(token: str, hashed: str) -> bool:
    """
    Verify a plaintext token against the stored bcrypt hash.
    """
    try:
        return bcrypt.checkpw(token.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False