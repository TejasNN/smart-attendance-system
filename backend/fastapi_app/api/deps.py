# backend/fastapi_app/api/deps.py
from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.fastapi_app.core.security import decode_jwt_token
from backend.fastapi_app.db.postgres_db import PostgresDB

bearer_scheme = HTTPBearer(auto_error=False)


def admin_required(creds: HTTPAuthorizationCredentials = 
                   Depends(bearer_scheme)) -> Dict[str, Any]:
    """
    FastAPI dependency that:
      1) extracts Bearer token
      2) decodes JWT
      3) ensures claim role == 'admin'
      4) verifies the admin user exists in Postgres and is_active == TRUE

    Returns the decoded claims (so handlers can access employee_id, username, etc.)
    Raises HTTPException(401/403) on failure.
    """
    # 1. Token present?
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Authorization credentials missing"
        )
    
    token = creds.credentials
    
    # 2. Decode JWT
    try:
        claims = decode_jwt_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or expired token"
        )
    
    # Role check
    role = claims.get("role")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin role required"
        )
    
    employee_id = claims.get("employee_id")
    if employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token: missing employee id"
        )
    
    # validate admin in Postgres
    pg = PostgresDB()

    try:
        pg.cursor.execute(
            """
            SELECT username, is_active 
            FROM users 
            WHERE employee_id = %s 
            LIMIT 1;
            """, (employee_id,)
        )
        row = pg.cursor.fetchone()
    except Exception:
        # close connection and re-raise as 500
        try:
            pg.cursor.close()
            pg.conn.close()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Database error while verifying admin"
        )
    finally:
        # cleanup connection
        try:
            pg.cursor.close()
            pg.conn.close()
        except Exception:
            pass

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Admin user not found"
        )
    
    if not row.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin account is not active"
        )
    
    # Optionally we can return a consolidated dict of claims + username
    claims["username"] = row.get("username")

    return claims
