from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ValidateInvitationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    token: str = Field(min_length=32, max_length=512)


class AcceptInvitationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    token: str = Field(min_length=32, max_length=512)
    password: SecretStr = Field(min_length=12, max_length=128)
    profile: "InvitationProfileRequest"


class InvitationProfileRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(
        default=None,
        pattern=r"^\+[1-9][0-9]{6,14}$",
    )
    job_title: str | None = Field(default=None, max_length=150)
    department: str | None = Field(default=None, max_length=150)
    timezone: str = Field(default="Asia/Shanghai", max_length=100)
    language: str = Field(default="en", max_length=10)


AcceptInvitationRequest.model_rebuild()
