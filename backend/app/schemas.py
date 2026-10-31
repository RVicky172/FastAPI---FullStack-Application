"""
Pydantic models = the "contract" of the API.

- *Create / *Update models validate what the client SENDS (request body).
- *Out models control what we RETURN (response_model). Anything not listed
  here (like hashed_password) is filtered out automatically.

from_attributes=True lets Pydantic read SQLAlchemy objects (user.id,
user.username...) instead of only dicts.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class SessionOut(BaseModel):
    """One active login, from the tokens table."""

    model_config = ConfigDict(from_attributes=True)

    jti: str
    created_at: datetime
    expires_at: datetime
    user_agent: str | None
    current: bool = False  # True for the token used to make this request


# ---------- Todos ----------
class TodoCreate(BaseModel):
    # str_strip_whitespace turns "  buy milk  " into "buy milk" before validation
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class TodoUpdate(BaseModel):
    """All fields optional -> used for PATCH (partial update)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool | None = None


class TodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    completed: bool
    created_at: datetime
    owner_id: uuid.UUID
