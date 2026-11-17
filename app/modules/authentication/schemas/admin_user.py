from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class CreateAdminUserRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    role: Literal["admin", "staff"]
