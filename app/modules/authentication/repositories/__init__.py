from app.modules.authentication.repositories.admin_totp_credential import (
    AdminTotpCredentialRepository,
)
from app.modules.authentication.repositories.admin_user import (
    AdminUserRepository,
)
from app.modules.authentication.repositories.admin_user_profile import (
    AdminUserProfileRepository,
)
from app.modules.authentication.repositories.admin_webauthn_credential import (
    AdminWebauthnCredentialRepository,
)
from app.modules.authentication.repositories.auth_challenge import (
    AuthChallengeRepository,
)
from app.modules.authentication.repositories.auth_recovery_code import (
    AuthRecoveryCodeRepository,
)
from app.modules.authentication.repositories.auth_session import (
    AdminSessionRepository,
)
from app.modules.authentication.repositories.permission import (
    PermissionRepository,
)
from app.modules.authentication.repositories.role import (
    RoleRepository,
)
from app.modules.authentication.repositories.role_permission import (
    RolePermissionRepository,
)
from app.modules.authentication.repositories.user_role import (
    UserRoleRepository,
)

__all__ = [
    "AdminSessionRepository",
    "AdminTotpCredentialRepository",
    "AdminUserRepository",
    "AdminUserProfileRepository",
    "AdminWebauthnCredentialRepository",
    "AuthChallengeRepository",
    "AuthRecoveryCodeRepository",
    "PermissionRepository",
    "RolePermissionRepository",
    "RoleRepository",
    "UserRoleRepository",
]
