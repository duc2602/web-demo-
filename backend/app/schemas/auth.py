from pydantic import BaseModel, Field


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class NewUser(Credentials):
    role: str = "user"


class PasswordReset(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    recovery_key: str = Field(min_length=32, max_length=256, repr=False)
    new_password: str = Field(min_length=1, max_length=128, repr=False)


class UserActiveUpdate(BaseModel):
    is_active: bool