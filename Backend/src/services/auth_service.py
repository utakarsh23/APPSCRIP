from datetime import datetime
from fastapi import HTTPException, status
from supabase import Client
from src.Schema.User import UserModel
from src.Schema.UserIO import UserSignupRequest, UserLoginRequest, UserResponse, TokenResponse
from src.utils.security import get_password_hash, verify_password, create_access_token


def get_user_by_id(db: Client, user_id: str) -> UserModel | None:
    response = db.table("users").select("*").eq("id", user_id).execute()
    if response.data and len(response.data) > 0:
        return UserModel(**response.data[0])
    return None


def get_user_by_username(db: Client, username: str) -> UserModel | None:
    response = db.table("users").select("*").eq("username", username).execute()
    if response.data and len(response.data) > 0:
        return UserModel(**response.data[0])
    return None


def get_user_by_email(db: Client, email: str) -> UserModel | None:
    response = db.table("users").select("*").eq("email", email).execute()
    if response.data and len(response.data) > 0:
        return UserModel(**response.data[0])
    return None


def signup_user(db: Client, request: UserSignupRequest) -> UserResponse:
    if get_user_by_username(db, request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    if get_user_by_email(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(request.password)
    now = datetime.utcnow().isoformat()
    user_data = {
        "email": request.email,
        "username": request.username,
        "password": hashed_password,
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }

    response = db.table("users").insert(user_data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user record"
        )

    created_user = response.data[0]
    return UserResponse(
        id=str(created_user["id"]),
        email=created_user["email"],
        username=created_user["username"],
        created_at=datetime.fromisoformat(created_user["created_at"].replace("Z", "+00:00"))
    )


def login_user(db: Client, request: UserLoginRequest) -> TokenResponse:
    user = None
    if request.email:
        user = get_user_by_email(db, request.email)
    elif request.username:
        user = get_user_by_username(db, request.username)

    if not user or not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token = create_access_token(
        data={"id": str(user.id), "username": user.username, "email": user.email}
    )
    return TokenResponse(access_token=access_token, token_type="bearer")
