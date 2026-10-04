from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user import MembershipTier, UserRole


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserProfileUpdate(BaseModel):
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    email: str | None = Field(default=None, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    phone: str | None = None
    email: str | None = None
    membership_tier: MembershipTier
    membership_points: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    message: str = "Login successful"
