"""Auth routes — login by mobile number (no registration for demo)"""

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from src.api.dependencies import DBSession, CurrentUserId
from src.core.security import create_access_token
from src.db.models.user import User

router = APIRouter()


class LoginRequest(BaseModel):
    mobile_number: str | None = None
    udyam_registration: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    role: str


class UserResponse(BaseModel):
    id: str
    mobile_number: str
    name: str
    email: str | None
    role: str
    organization_name: str | None
    udyam_registration: str | None

    model_config = {"from_attributes": True}


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: DBSession):
    """Login with mobile number or Udyam registration number."""
    if not request.mobile_number and not request.udyam_registration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either mobile_number or udyam_registration.",
        )

    if request.udyam_registration:
        # Seller login via Udyam Registration Number
        result = await db.execute(
            select(User).where(
                User.udyam_registration == request.udyam_registration.strip().upper()
            )
        )
    else:
        # Admin/fallback login via mobile number
        result = await db.execute(
            select(User).where(User.mobile_number == request.mobile_number)
        )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please check your credentials.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    token = create_access_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=token,
        user_id=str(user.id),
        name=user.name,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user_id: CurrentUserId, db: DBSession):
    """Get current user profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=str(user.id),
        mobile_number=user.mobile_number,
        name=user.name,
        email=user.email,
        role=user.role,
        organization_name=user.organization_name,
        udyam_registration=user.udyam_registration,
    )
