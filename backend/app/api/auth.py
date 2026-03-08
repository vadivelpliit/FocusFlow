import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..auth.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    verify_password,
)
from ..crud import (
    create_password_reset_token,
    create_user,
    delete_password_reset_token,
    get_password_reset_token,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginRequest(BaseModel):
    email_or_username: str  # user can enter either
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def _send_reset_email(to_email: str, reset_link: str) -> bool:
    """Send password reset email via SMTP. Returns True if sent."""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("EMAIL_FROM", user or "noreply@focusflow.app")
    if not host or not user or not password:
        return False
    try:
        msg = MIMEMultipart()
        msg["Subject"] = "FocusFlow – Reset your password"
        msg["From"] = from_addr
        msg["To"] = to_email
        body = f"""You requested a password reset. Click the link below (valid for 1 hour):\n\n{reset_link}\n\nIf you didn't request this, ignore this email."""
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        return False


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, body.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if get_user_by_username(db, body.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user = create_user(db, body.email, body.username, hash_password(body.password))
    token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, username=user.username),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, body.email_or_username) or get_user_by_username(db, body.email_or_username)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email/username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, username=user.username),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email, username=current_user.username)


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, body.email)
    if not user:
        return {"message": "If that email is registered, you will receive a reset link."}
    token = generate_reset_token()
    expires = datetime.utcnow() + timedelta(hours=1)
    create_password_reset_token(db, user.id, token, expires)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    reset_link = f"{frontend_url}/reset-password?token={token}"
    if _send_reset_email(user.email, reset_link):
        return {"message": "If that email is registered, you will receive a reset link."}
    return {"message": "Email is not configured. For development, use this reset link:", "reset_link": reset_link}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    row = get_password_reset_token(db, body.token)
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user = get_user_by_id(db, row.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    delete_password_reset_token(db, body.token)
    return {"message": "Password updated. You can now log in."}
