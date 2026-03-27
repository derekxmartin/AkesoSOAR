"""Authentication API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.dependencies import get_db
from akeso_soar.services.auth import (
    TOKEN_TYPE_REFRESH,
    authenticate_user,
    create_token_pair,
    decode_token,
    generate_totp_secret,
    get_totp_uri,
    get_user_by_id,
    verify_totp,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MFASetupResponse(BaseModel):
    secret: str
    uri: str


class MFAVerifyRequest(BaseModel):
    code: str


class MFAVerifyResponse(BaseModel):
    verified: bool


# ---------------------------------------------------------------------------
# Auth dependency (must be defined before endpoints that use it)
# ---------------------------------------------------------------------------


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    return authorization[7:]


async def get_current_user_payload(authorization: str | None = Header(None)) -> dict:
    """Extract and validate JWT from Authorization header. Used as a FastAPI dependency."""
    token = _extract_bearer_token(authorization)
    try:
        payload = decode_token(token)
    except JWTError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from err
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an access token")
    return payload


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # If MFA is enabled, require a valid TOTP code
    if user.mfa_enabled:
        if not body.totp_code:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MFA code required")
        if not verify_totp(user.mfa_secret, body.totp_code):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    return create_token_pair(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except JWTError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from err

    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    user = await get_user_by_id(db, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return create_token_pair(user)


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_payload),
):
    user = await get_user_by_id(db, uuid.UUID(current_user["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    secret = generate_totp_secret()
    user.mfa_secret = secret
    await db.flush()

    return MFASetupResponse(secret=secret, uri=get_totp_uri(secret, user.username))


@router.post("/mfa/verify", response_model=MFAVerifyResponse)
async def mfa_verify(
    body: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_payload),
):
    user = await get_user_by_id(db, uuid.UUID(current_user["sub"]))
    if user is None or not user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not set up")

    if not verify_totp(user.mfa_secret, body.code):
        return MFAVerifyResponse(verified=False)

    user.mfa_enabled = True
    await db.flush()
    return MFAVerifyResponse(verified=True)
