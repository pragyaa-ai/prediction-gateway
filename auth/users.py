from passlib.context import CryptContext
from typing import Optional, Dict
from datetime import datetime, timedelta
from jose import JWTError, jwt

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key-change-in-production-use-env-variable"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Super admin users
SUPER_ADMIN_USERS = {
    "gulshan@pragyaa.ai": {
        "name": "Gulshan Mehta",
        "email": "gulshan@pragyaa.ai",
        "password_hash": pwd_context.hash("changeme123"),  # Change in production
        "role": "super_admin"
    },
    "manoj@pragyaa.ai": {
        "name": "Manoj Gulati",
        "email": "manoj@pragyaa.ai",
        "password_hash": pwd_context.hash("changeme123"),  # Change in production
        "role": "super_admin"
    },
    "krishna@pragyaa.ai": {
        "name": "Krishna Bajpai",
        "email": "krishna@pragyaa.ai",
        "password_hash": pwd_context.hash("changeme123"),  # Change in production
        "role": "super_admin"
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Authenticate a user by email and password"""
    user = SUPER_ADMIN_USERS.get(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = SUPER_ADMIN_USERS.get(email)
        return user
    except JWTError:
        return None
