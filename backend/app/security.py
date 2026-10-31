"""
Password hashing + JWT creation/verification + the dependencies that
protect routes.

JWT flow:
  1. POST /api/auth/login with username+password
  2. Server verifies the password, saves a row in the `tokens` table and
     returns a signed token: {"sub": user_id, "jti": token_id, "exp": ...}
  3. Client sends it on every request:  Authorization: Bearer <token>
  4. get_current_token() checks, in order:
       a) signature + expiry      (PyJWT - no DB needed)
       b) the jti row exists and is not revoked   (DB - this enables logout)
     Any failure -> 401.
  5. POST /api/auth/logout sets revoked_at, so step 4b fails from then on.
"""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from .database import get_db
from .models import Token, User

# ---------- Passwords ----------
# PBKDF2 from the standard library: slow on purpose, salted per user.
_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, expected = stored.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    # compare_digest avoids timing attacks
    return hmac.compare_digest(digest.hex(), expected)


# ---------- JWT ----------
def create_access_token(db: Session, user: User, user_agent: str | None = None) -> str:
    """Create a JWT and record it in the tokens table."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = uuid.uuid4().hex  # unique id for THIS token

    db.add(Token(jti=jti, user_id=user.id, created_at=now, expires_at=expires_at,
                 user_agent=(user_agent or "")[:300] or None))
    db.commit()

    payload = {"sub": str(user.id), "jti": jti, "iat": now, "exp": expires_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# HTTPBearer reads the "Authorization: Bearer <token>" header for us and
# adds an "Authorize" button in the Swagger UI (/docs).
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail,
                         headers={"WWW-Authenticate": "Bearer"})


def get_current_token(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Token:
    """Dependency: the valid, non-revoked Token row for this request."""
    if creds is None:
        raise _unauthorized("Invalid or expired token")
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid or expired token")

    token = db.get(Token, payload.get("jti"))
    if token is None or str(token.user_id) != payload.get("sub"):
        raise _unauthorized("Invalid or expired token")
    if token.revoked_at is not None:
        raise _unauthorized("Token has been revoked")
    return token


def get_current_user(token: Token = Depends(get_current_token)) -> User:
    """Dependency: add `user = Depends(get_current_user)` to any route to protect it."""
    return token.user
