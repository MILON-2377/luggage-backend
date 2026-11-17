import uuid

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.generators.slug_generator import AbstractSlugGenerator
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.authentication.contracts.repositories import (
    AbstractAdminUserProfileRepository,
    AbstractAdminUserRepository,
    AbstractRoleRepository,
    AbstractUserRoleRepository,
)
from app.modules.authentication.contracts.services.account_provisioning import (
    AbstractAccountProvisioningService,
)
from app.modules.authentication.contracts.services.invitation import (
    AbstractInvitationService,
)
from app.modules.authentication.dtos.account_provisioning import (
    CreateInvitedAccountDTO,
)
from app.modules.authentication.dtos.invitation import InvitationResultDTO
from app.modules.authentication.enums import AdminUserStatus, RoleType
from app.modules.authentication.models import AdminUser, AdminUserProfile, UserRole


class AccountProvisioningService(AbstractAccountProvisioningService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        invitation_service: AbstractInvitationService,
        id_generator: AbstractIDGenerator,
        slug_generator: AbstractSlugGenerator,
    ) -> None:
        self.uow = uow
        self.invitation_service = invitation_service
        self.id_generator = id_generator
        self.slug_generator = slug_generator

    async def create_invited_account(
        self,
        data: CreateInvitedAccountDTO,
    ) -> InvitationResultDTO:
        email = data.email.strip().lower()
        role_slug = self.slug_generator.generate(data.role_slug)

        if role_slug not in RoleType.provisionable():
            raise ValidationError("Only admin and staff accounts can be provisioned.")

        user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        profile_repository = self.uow.get_repository(AbstractAdminUserProfileRepository)
        role_repository = self.uow.get_repository(AbstractRoleRepository)
        user_role_repository = self.uow.get_repository(AbstractUserRoleRepository)

        if await user_repository.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists.")

        role = await role_repository.get_by_slug(role_slug)
        if role is None:
            raise NotFoundError("The requested role was not found.")

        admin_user_id: uuid.UUID = self.id_generator.generate()

        user_repository.create(
            AdminUser(
                id=admin_user_id,
                email=email,
                password_hash=None,
                status=AdminUserStatus.INVITED,
            )
        )

        profile_repository.create(
            AdminUserProfile(
                id=self.id_generator.generate(),
                admin_user_id=admin_user_id,
            )
        )

        user_role_repository.create(
            UserRole(
                admin_user_id=admin_user_id,
                role_id=role.id,
                assigned_by=data.created_by,
            )
        )

        # Flush so the user row exists for the invitation's row lock, and a
        # duplicate-email unique violation surfaces here.
        await self.uow.flush()

        # InvitationService renders and enqueues the email itself and does
        # not commit, so everything below commits atomically.
        invitation_result = await self.invitation_service.create_invitation(
            admin_user_id
        )

        await self.uow.commit()
        return invitation_result
