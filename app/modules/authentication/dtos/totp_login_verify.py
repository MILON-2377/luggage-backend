from pydantic import BaseModel, ConfigDict, SecretStr


class TotpLoginVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: SecretStr
    code: SecretStr