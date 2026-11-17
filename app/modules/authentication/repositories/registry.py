from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.modules.authentication.contracts.repositories import (
    AbstractAdminSessionRepository,
    AbstractAdminTotpCredentialRepository,
    AbstractAdminUserProfileRepository,
    AbstractAdminUserRepository,
    AbstractAdminWebauthnCredentialRepository,
    AbstractAuthChallengeRepository,
    AbstractAuthRecoveryCodeRepository,
    AbstractPermissionRepository,
    AbstractRolePermissionRepository,
    AbstractRoleRepository,
    AbstractUserRoleRepository,
)
from app.modules.authentication.repositories import (
    AdminSessionRepository,
    AdminTotpCredentialRepository,
    AdminUserProfileRepository,
    AdminUserRepository,
    AdminWebauthnCredentialRepository,
    AuthChallengeRepository,
    AuthRecoveryCodeRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRoleRepository,
)


def register_authentication_repositories(
    uow: AbstractUnitOfWork,
) -> None:
    session = uow.session

    repositories = (
        (AbstractAdminUserRepository, AdminUserRepository),
        (AbstractAdminUserProfileRepository, AdminUserProfileRepository),
        (AbstractRoleRepository, RoleRepository),
        (AbstractUserRoleRepository, UserRoleRepository),
        (AbstractAuthChallengeRepository, AuthChallengeRepository),
        (AbstractAdminSessionRepository, AdminSessionRepository),
        (AbstractAdminTotpCredentialRepository, AdminTotpCredentialRepository),
        (AbstractAdminWebauthnCredentialRepository, AdminWebauthnCredentialRepository),
        (AbstractAuthRecoveryCodeRepository, AuthRecoveryCodeRepository),
        (AbstractPermissionRepository, PermissionRepository),
        (AbstractRolePermissionRepository, RolePermissionRepository),
    )

    for contract, implementation in repositories:
        uow.register_repository(
            contract,
            implementation(session),
        )
