from app.modules.authentication.contracts.repositories.admin_session import (
    AbstractAdminSessionRepository,
)
from app.modules.authentication.contracts.repositories.admin_totp_credential import (
    AbstractAdminTotpCredentialRepository,
)
from app.modules.authentication.contracts.repositories.admin_user import (
    AbstractAdminUserRepository,
)
from app.modules.authentication.contracts.repositories.admin_user_profile import (
    AbstractAdminUserProfileRepository,
)
from app.modules.authentication.contracts.repositories.admin_webauthn_credential import (
    AbstractAdminWebauthnCredentialRepository,
)
from app.modules.authentication.contracts.repositories.auth_challenge import (
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.repositories.auth_recovery_code import (
    AbstractAuthRecoveryCodeRepository,
)
from app.modules.authentication.contracts.repositories.permission import (
    AbstractPermissionRepository,
)
from app.modules.authentication.contracts.repositories.role import (
    AbstractRoleRepository,
)
from app.modules.authentication.contracts.repositories.role_permission import (
    AbstractRolePermissionRepository,
)
from app.modules.authentication.contracts.repositories.user_role import (
    AbstractUserRoleRepository,
)

__all__ = [
    "AbstractAdminSessionRepository",
    "AbstractAdminTotpCredentialRepository",
    "AbstractAdminUserRepository",
    "AbstractAdminUserProfileRepository",
    "AbstractAdminWebauthnCredentialRepository",
    "AbstractAuthChallengeRepository",
    "AbstractAuthRecoveryCodeRepository",
    "AbstractPermissionRepository",
    "AbstractRolePermissionRepository",
    "AbstractRoleRepository",
    "AbstractUserRoleRepository",
]
