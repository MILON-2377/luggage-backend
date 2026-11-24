from fastapi import APIRouter

from app.api.v1.admin.routes.authentication import initial_mfa_setup
from app.api.v1.admin.routes.authentication.forgot_password import (
    router as forgot_password_router,
)
from app.api.v1.admin.routes.authentication.initial_mfa_setup_resend import (
    router as initial_mfa_setup_resend_router,
)
from app.api.v1.admin.routes.authentication.initial_mfa_setup_totp import (
    router as initial_mfa_setup_totp_router,
)
from app.api.v1.admin.routes.authentication.initial_totp_verification import (
    router as initial_totp_verification_router,
)
from app.api.v1.admin.routes.authentication.login import router as login_router
from app.api.v1.admin.routes.authentication.logout import router as logout_router
from app.api.v1.admin.routes.authentication.me import router as me_router
from app.api.v1.admin.routes.authentication.passkey_login import (
    router as passkey_login_router,
)
from app.api.v1.admin.routes.authentication.passkey_login_verify import (
    router as passkey_login_verify_router,
)
from app.api.v1.admin.routes.authentication.passkey_registration_options import (
    router as passkey_registration_options_router,
)
from app.api.v1.admin.routes.authentication.passkey_registration_verify import (
    router as passkey_registration_verify_router,
)
from app.api.v1.admin.routes.authentication.recovery_code_login_verify import (
    router as recovery_code_login_verify_router,
)
from app.api.v1.admin.routes.authentication.refresh import router as refresh_router
from app.api.v1.admin.routes.authentication.totp_login_verify import (
    router as totp_login_verify_router,
)
from app.api.v1.admin.routes.authentication.verify_password_reset import (
    router as verify_password_reset_router,
)

router = APIRouter(
    prefix="/auth",
    tags=["Admin Authentication"],
)

router.include_router(initial_mfa_setup.router)
router.include_router(initial_mfa_setup_totp_router)
router.include_router(initial_totp_verification_router)
router.include_router(initial_mfa_setup_resend_router)
router.include_router(login_router)
router.include_router(passkey_login_router)
router.include_router(passkey_login_verify_router)
router.include_router(totp_login_verify_router)
router.include_router(recovery_code_login_verify_router)
router.include_router(passkey_registration_options_router)
router.include_router(passkey_registration_verify_router)
router.include_router(logout_router)
router.include_router(me_router)
router.include_router(refresh_router)
router.include_router(forgot_password_router)
router.include_router(verify_password_reset_router)
