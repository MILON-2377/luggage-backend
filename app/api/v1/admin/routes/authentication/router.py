from fastapi import APIRouter

from app.api.v1.admin.routes.authentication import initial_mfa_setup
from app.api.v1.admin.routes.authentication.initial_mfa_setup_resend import (
    router as initial_mfa_setup_resend_router,
)
from app.api.v1.admin.routes.authentication.initial_mfa_setup_totp import (
    router as initial_mfa_setup_totp_router,
)
from app.api.v1.admin.routes.authentication.initial_totp_verification import (
    router as initial_totp_verificatioin_router,
)

router = APIRouter(
    prefix="/auth",
    tags=["Admin Authentication"],
)

router.include_router(initial_mfa_setup.router)
router.include_router(initial_mfa_setup_totp_router)
router.include_router(initial_totp_verificatioin_router)
router.include_router(initial_mfa_setup_resend_router)
