
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class PasskeyLoginOptionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: SecretStr


class PasskeyLoginOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_key: dict[str, Any] = Field(
        description="WebAuthn PublicKeyCredentialRequestOptions for navigator.credentials.get()."
    )
