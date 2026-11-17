import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors.base import ConflictError, NotFoundError, ValidationError
from app.modules.authentication.contracts.repositories.admin_user import (
    AbstractAdminUserRepository,
)
from app.modules.authentication.contracts.repositories.admin_user_profile import (
    AbstractAdminUserProfileRepository,
)
from app.modules.authentication.contracts.repositories.role import (
    AbstractRoleRepository,
)
from app.modules.authentication.contracts.repositories.user_role import (
    AbstractUserRoleRepository,
)
from app.modules.authentication.dtos.account_provisioning import (
    CreateInvitedAccountDTO,
)
from app.modules.authentication.dtos.invitation import InvitationResultDTO
from app.modules.authentication.enums.admin_user_status import AdminUserStatus
from app.modules.authentication.models.admin_user import AdminUser
from app.modules.authentication.models.admin_user_profile import AdminUserProfile
from app.modules.authentication.models.user_role import UserRole
from app.modules.authentication.services.account_provisioning import (
    AccountProvisioningService,
)
from app.modules.media.models.media_asset import MediaAsset

pytestmark = pytest.mark.asyncio


class Env(SimpleNamespace):
    """Typed-ish holder for the service and its fakes."""


def _default_dto(**overrides) -> CreateInvitedAccountDTO:
    values = {
        "email": " Employee@Example.com ",
        "role_slug": "Staff",
        "created_by": uuid.uuid4(),
    }
    values.update(overrides)
    return CreateInvitedAccountDTO(**values)


@pytest.fixture
def env() -> Env:
    uow = MagicMock()
    uow.flush = AsyncMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()

    user_repository = MagicMock()
    user_repository.get_by_email = AsyncMock(return_value=None)

    profile_repository = MagicMock()

    role = SimpleNamespace(id=uuid.uuid4())
    role_repository = MagicMock()
    role_repository.get_by_slug = AsyncMock(return_value=role)

    user_role_repository = MagicMock()

    repositories = {
        AbstractAdminUserRepository: user_repository,
        AbstractAdminUserProfileRepository: profile_repository,
        AbstractRoleRepository: role_repository,
        AbstractUserRoleRepository: user_role_repository,
    }
    uow.get_repository.side_effect = repositories.__getitem__

    invitation_result = InvitationResultDTO(
        admin_user_id=uuid.uuid4(),
        email="employee@example.com",
        invitation_token="test-invitation-token",
        expires_at=datetime.now(UTC),
    )
    invitation_service = MagicMock()
    invitation_service.create_invitation = AsyncMock(return_value=invitation_result)

    id_generator = MagicMock()
    id_generator.generate.side_effect = lambda: uuid.uuid4()

    slug_generator = MagicMock()
    slug_generator.generate.return_value = "staff"

    service = AccountProvisioningService(
        uow=uow,
        invitation_service=invitation_service,
        id_generator=id_generator,
        slug_generator=slug_generator,
    )

    return Env(
        service=service,
        uow=uow,
        users=user_repository,
        profiles=profile_repository,
        roles=role_repository,
        user_roles=user_role_repository,
        role=role,
        invitations=invitation_service,
        slugs=slug_generator,
        invitation_result=invitation_result,
    )


def assert_nothing_persisted(env: Env) -> None:
    env.users.create.assert_not_called()
    env.profiles.create.assert_not_called()
    env.user_roles.create.assert_not_called()
    env.invitations.create_invitation.assert_not_awaited()
    env.uow.commit.assert_not_awaited()


class TestSuccess:
    async def test_creates_account_profile_role_and_invitation(
        self, env: Env
    ) -> None:
        data = _default_dto()

        result = await env.service.create_invited_account(data)

        assert result is env.invitation_result

        admin_user = env.users.create.call_args.args[0]
        assert isinstance(admin_user, AdminUser)
        assert admin_user.email == "employee@example.com"
        assert admin_user.password_hash is None
        assert admin_user.status == AdminUserStatus.INVITED

        profile = env.profiles.create.call_args.args[0]
        assert isinstance(profile, AdminUserProfile)
        assert profile.admin_user_id == admin_user.id
        assert profile.id != admin_user.id

        user_role = env.user_roles.create.call_args.args[0]
        assert isinstance(user_role, UserRole)
        assert user_role.admin_user_id == admin_user.id
        assert user_role.role_id == env.role.id
        assert user_role.assigned_by == data.created_by

        env.invitations.create_invitation.assert_awaited_once_with(admin_user.id)

    async def test_each_entity_is_created_exactly_once(self, env: Env) -> None:
        await env.service.create_invited_account(_default_dto())

        env.users.create.assert_called_once()
        env.profiles.create.assert_called_once()
        env.user_roles.create.assert_called_once()

    async def test_flushes_before_invitation_and_commits_last(
        self, env: Env
    ) -> None:
        order: list[str] = []
        env.uow.flush.side_effect = lambda: order.append("flush")
        env.invitations.create_invitation.side_effect = lambda _id: (
            order.append("invite") or env.invitation_result
        )
        env.uow.commit.side_effect = lambda: order.append("commit")

        await env.service.create_invited_account(_default_dto())

        assert order == ["flush", "invite", "commit"]

    async def test_normalizes_email_and_slugifies_role(self, env: Env) -> None:
        env.slugs.generate.return_value = "admin"

        await env.service.create_invited_account(
            _default_dto(email="  ADMIN@EXAMPLE.COM  ", role_slug="  Admin  ")
        )

        env.slugs.generate.assert_called_once_with("  Admin  ")
        env.users.get_by_email.assert_awaited_once_with("admin@example.com")
        env.roles.get_by_slug.assert_awaited_once_with("admin")


class TestValidation:
    @pytest.mark.parametrize("slug", ["super-admin", "unknown", ""])
    async def test_rejects_non_provisionable_role(
        self, env: Env, slug: str
    ) -> None:
        env.slugs.generate.return_value = slug

        with pytest.raises(ValidationError):
            await env.service.create_invited_account(_default_dto())

        env.users.get_by_email.assert_not_awaited()
        env.roles.get_by_slug.assert_not_awaited()
        assert_nothing_persisted(env)

    async def test_rejects_existing_email(self, env: Env) -> None:
        env.users.get_by_email.return_value = SimpleNamespace(id=uuid.uuid4())

        with pytest.raises(ConflictError):
            await env.service.create_invited_account(_default_dto())

        env.roles.get_by_slug.assert_not_awaited()
        assert_nothing_persisted(env)

    async def test_rejects_missing_role(self, env: Env) -> None:
        env.roles.get_by_slug.return_value = None

        with pytest.raises(NotFoundError):
            await env.service.create_invited_account(_default_dto())

        assert_nothing_persisted(env)


class TestFailureHandling:
    async def test_flush_failure_skips_invitation_and_commit(
        self, env: Env
    ) -> None:
        env.uow.flush.side_effect = RuntimeError("Database flush failed")

        with pytest.raises(RuntimeError, match="Database flush failed"):
            await env.service.create_invited_account(_default_dto())

        env.invitations.create_invitation.assert_not_awaited()
        env.uow.commit.assert_not_awaited()

    async def test_invitation_failure_skips_commit(self, env: Env) -> None:
        env.invitations.create_invitation.side_effect = RuntimeError(
            "Invitation creation failed"
        )

        with pytest.raises(RuntimeError, match="Invitation creation failed"):
            await env.service.create_invited_account(_default_dto())

        env.uow.flush.assert_awaited_once()
        env.uow.commit.assert_not_awaited()

    async def test_commit_failure_propagates(self, env: Env) -> None:
        env.uow.commit.side_effect = RuntimeError("Commit failed")

        with pytest.raises(RuntimeError, match="Commit failed"):
            await env.service.create_invited_account(_default_dto())