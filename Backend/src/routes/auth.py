from fastapi import APIRouter, Depends, status
from supabase import Client
from src.utils.database import get_db
from src.Schema.UserIO import UserSignupRequest, UserLoginRequest, UserResponse, TokenResponse
from src.services.auth_service import signup_user, login_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    request: UserSignupRequest,
    db: Client = Depends(get_db)
) -> UserResponse:
    return signup_user(db, request)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    request: UserLoginRequest,
    db: Client = Depends(get_db)
) -> TokenResponse:
    return login_user(db, request)
