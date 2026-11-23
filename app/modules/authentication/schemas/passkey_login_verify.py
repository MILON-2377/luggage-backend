
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class PasskeyLoginVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: SecretStr

    credential: dict[str, Any] = Field(
        description="WebAuthn PublicKeyCredential assertion returned by the browser."
    )



class PasskeyLoginVerifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authenticated: bool
    message: str