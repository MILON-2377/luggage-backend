from pydantic import BaseModel, ConfigDict, SecretStr


class RecoveryCodeLoginVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: SecretStr
    recovery_code: SecretStr