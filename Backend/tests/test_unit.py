from src.utils.chunking import chunk_text
from src.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_small():
    text = "Hello world! This is a simple test."
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_splitting():
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def test_password_hashing():
    password = "SecretPassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_creation_and_decoding():
    payload = {"id": "12345", "email": "test@example.com"}
    token = create_access_token(payload)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded.get("id") == "12345"
    assert decoded.get("email") == "test@example.com"


def test_jwt_token_invalid():
    assert decode_access_token("invalid.jwt.token") is None
