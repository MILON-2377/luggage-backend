from pydantic import BaseModel, ConfigDict


class LogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authenticated: bool
    message: str