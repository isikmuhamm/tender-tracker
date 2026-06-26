import pytest
from datetime import timedelta
import jwt
from src.auth import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM

def test_password_hashing():
    password = "secretpassword"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_jwt_token_creation():
    data = {"sub": "admin"}
    token = create_access_token(data=data, expires_delta=timedelta(minutes=10))
    
    # Token'ı deşifre et ve içeriğini doğrula
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin"
    assert "exp" in payload
