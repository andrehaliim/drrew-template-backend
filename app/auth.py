from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os
import uuid
import random
import string

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---- Password hashing ----

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---- JWT token creation ----

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> tuple[str, str, datetime]:
    """Return (token_string, jti, expires_at) — jti & expires_at dipakai untuk disimpan di DB."""
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti, expire


# ---- JWT token verification ----

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ---- OTP functions ----
OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", 10))


def generate_otp_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def hash_otp(otp_code: str) -> str:
    return pwd_context.hash(otp_code)


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    return pwd_context.verify(plain_otp, hashed_otp)