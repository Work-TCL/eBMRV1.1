import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: uuid.UUID, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class AuthenticatedActor:
    """Resolved server-side from a trusted token. Never trust a client-supplied actor field for
    authority decisions (MUT-FR-002 equivalent)."""

    def __init__(self, user_id: uuid.UUID, username: str) -> None:
        self.user_id = user_id
        self.username = username


def get_current_actor(token: str = Depends(oauth2_scheme)) -> AuthenticatedActor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        username = payload.get("username")
        if user_id is None or username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return AuthenticatedActor(user_id=uuid.UUID(user_id), username=username)
