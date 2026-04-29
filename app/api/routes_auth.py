from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthPayload, LoginInput, RegisterInput, UserSummary

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthPayload, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterInput, db: Session = Depends(get_db)) -> AuthPayload:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already exists for that email.")

    user = User(
        display_name=payload.display_name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthPayload(token=create_access_token(user.id, user.email), user=UserSummary.model_validate(user))


@router.post("/login", response_model=AuthPayload)
def login(payload: LoginInput, db: Session = Depends(get_db)) -> AuthPayload:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    return AuthPayload(token=create_access_token(user.id, user.email), user=UserSummary.model_validate(user))


@router.get("/me", response_model=UserSummary)
def me(current_user: User = Depends(get_current_user)) -> UserSummary:
    return UserSummary.model_validate(current_user)

