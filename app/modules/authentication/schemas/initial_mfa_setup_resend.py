from pydantic import BaseModel, ConfigDict, EmailStr


class InitialMFASetupResendRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr


class InitialMFASetupResendResponse(BaseModel):
    message: str
