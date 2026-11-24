from pydantic import BaseModel, ConfigDict, EmailStr


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = (
        "If an eligible account exists, password recovery instructions "
        "will be sent to the registered email address."
    )