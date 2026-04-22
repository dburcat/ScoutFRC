from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional # Added Optional
from jose import jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

# Fix 1: Ensure SECRET_KEY is a string. 
# If it's missing from .env, this will raise an error immediately rather than crashing later.
# Force the type to str and provide an empty string default for the cast
SECRET_KEY: str = str(os.getenv("SECRET_KEY", ""))

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not found in environment variables. JWT cannot be signed.")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Fix 2: Use Optional[timedelta] so the default can be None
def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # SECRET_KEY is now guaranteed to be a str here
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt