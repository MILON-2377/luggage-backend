from pydantic import BaseModel, ConfigDict, SecretStr


class TotpLoginVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: SecretStr
    code: SecretStr


class TotpLoginVerifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authenticated: bool
    message: str