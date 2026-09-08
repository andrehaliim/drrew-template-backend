from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, RefreshToken
from app.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    RefreshTokenRequest,
    UserUpdate,
    ChangePasswordRequest,
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

from datetime import datetime, timedelta, timezone
from app.models import User, RefreshToken, PasswordResetToken
from app.schemas import (
    UserCreate, UserLogin, UserResponse, Token, RefreshTokenRequest,
    UserUpdate, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, generate_otp_code, hash_otp, verify_otp, OTP_EXPIRE_MINUTES,
)
from app.email import send_otp_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---- Dependency: ambil user dari access token ----

def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return user


# ---- Helper: buat & simpan sepasang token ----

def issue_tokens(user: User, db: Session) -> Token:
    access_token = create_access_token(data={"sub": user.email})
    refresh_token_str, jti, expires_at = create_refresh_token(data={"sub": user.email})

    token_record = RefreshToken(
        jti=jti,
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(token_record)
    db.commit()

    return Token(access_token=access_token, refresh_token=refresh_token_str)


# ---- POST /auth/register ----

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ---- POST /auth/login ----

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )

    return issue_tokens(user, db)


# ---- POST /auth/refresh ----

@router.post("/refresh", response_model=Token)
def refresh_token_endpoint(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    jti = payload.get("jti")
    token_record = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()

    if token_record is None or token_record.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is no longer valid (logged out or revoked)",
        )

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    token_record.revoked = True
    db.commit()

    return issue_tokens(user, db)


# ---- POST /auth/logout ----

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    jti = payload.get("jti")
    token_record = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()

    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    token_record.revoked = True
    db.commit()

    return {"message": "Logout successful"}

# ---- POST /auth/change-password ----

@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password does not match",
        )

    current_user.hashed_password = hash_password(body.new_password)

    # Revoke semua refresh token milik user ini — paksa login ulang di semua device
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id, RefreshToken.revoked == False
    ).update({"revoked": True})

    db.commit()

    return {"message": "Password changed successfully. Please login again."}

# ---- POST /auth/forgot-password ----

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    # Selalu balas pesan generik, biar endpoint ini gak bisa dipakai
    # buat cek "email ini terdaftar apa gak" (enumeration attack).
    generic_response = {"message": "If that email is registered, a reset code has been sent."}

    if not user:
        return generic_response

    # Invalidate kode lama yang belum dipakai, biar cuma 1 kode aktif per user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False,
    ).update({"used": True})

    otp_code = generate_otp_code()
    reset_token = PasswordResetToken(
        user_id=user.id,
        otp_hash=hash_otp(otp_code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES),
    )
    db.add(reset_token)
    db.commit()

    send_otp_email(user.email, otp_code)

    return generic_response


# ---- POST /auth/reset-password ----

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    invalid_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset code",
    )

    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise invalid_exception

    token_record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,
        )
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )

    if token_record is None or token_record.expires_at < datetime.now(timezone.utc):
        raise invalid_exception

    if not verify_otp(body.otp_code, token_record.otp_hash):
        raise invalid_exception

    user.hashed_password = hash_password(body.new_password)
    token_record.used = True

    # Sama kayak change-password: paksa login ulang di semua device
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked == False
    ).update({"revoked": True})

    db.commit()

    return {"message": "Password reset successfully. Please login."}    

# ---- GET /auth/me (contoh protected endpoint) ----

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ---- PATCH /auth/me ----

@router.patch("/me", response_model=UserResponse)
def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = body.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return current_user