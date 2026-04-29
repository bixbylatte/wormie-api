from pydantic import BaseModel, EmailStr, Field


class RegisterInput(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserSummary(BaseModel):
    id: int
    display_name: str
    email: EmailStr

    model_config = {"from_attributes": True}


class AuthPayload(BaseModel):
    token: str
    user: UserSummary

