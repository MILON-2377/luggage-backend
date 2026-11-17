import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.authentication.dtos.invitation import InvitationResultDTO
from app.modules.authentication.dtos.validate_invitation import ValidateInvitationDTO
from app.modules.authentication.enums.admin_user_status import AdminUserStatus
from app.modules.authentication.enums.challenge_type import ChallengeType
from app.modules.authentication.errors import (
    AccountNotEligibleForInvitationError,
    AccountNotFoundError,
    InvitationAlreadyUsedError,
    InvitationAttemptsExceededError,
    InvitationExpiredError,
    InvitationNotFoundError,
)
from app.modules.authentication.models.admin_user import AdminUser
from app.modules.authentication.models.auth_challenge import AuthChallenge
from app.modules.authentication.services.invitation import InvitationService
from app.modules.media.models.media_asset import MediaAsset
from app.modules.notification.dtos.email_outbox import EnqueueEmailDTO


@pytest.fixture
def dependencies():
    uow = MagicMock()
    token_hasher = MagicMock()
    id_generator = MagicMock()
    settings = MagicMock()

    settings.INVITATION_EXPIRE_HOURS = 24
    settings.INVITATION_MAX_ATTEMPTS = 5
    settings.FRONTEND_BASE_URL = "https://app.example.com"
    settings.INVITATION_ACCEPTANCE_PATH = "/accept-invitation"
    settings.APP_NAME = "Showroom"

    user_repository = AsyncMock()
    challenge_repository = AsyncMock()
    email_outbox_service = AsyncMock()
    email_renderer = MagicMock()

    email_renderer.render.return_value = MagicMock(
        subject="You've been invited to Showroom",
        html_content="<p>Accept your invitation</p>",
        text_content="Accept your invitation",
    )

    uow.get_repository.side_effect = lambda repository_type: (
        user_repository
        if repository_type.__name__ == "AbstractAdminUserRepository"
        else challenge_repository
    )

    token_hasher.hash_token.side_effect = lambda token: f"hashed:{token}"
    id_generator.generate.return_value = uuid.uuid4()

    service = InvitationService(
        uow=uow,
        token_hasher=token_hasher,
        id_generator=id_generator,
        email_outbox_service=email_outbox_service,
        email_renderer=email_renderer,
        settings=settings,
    )

    return {
        "service": service,
        "uow": uow,
        "token_hasher": token_hasher,
        "id_generator": id_generator,
        "settings": settings,
        "user_repository": user_repository,
        "challenge_repository": challenge_repository,
        "email_outbox_service": email_outbox_service,
        "email_renderer": email_renderer,
    }


def make_admin_user(
    status: AdminUserStatus = AdminUserStatus.INVITED,
) -> MagicMock:
    user = MagicMock(spec=AdminUser)
    user.id = uuid.uuid4()
    user.email = "employee@example.com"
    user.status = status
    return user


def make_challenge(
    *,
    consumed_at: datetime | None = None,
    expires_at: datetime | None = None,
    failed_attempts: int = 0,
    max_attempts: int = 5,
) -> MagicMock:
    challenge = MagicMock(spec=AuthChallenge)
    challenge.consumed_at = consumed_at
    challenge.expires_at = expires_at or (datetime.now(UTC) + timedelta(hours=1))
    challenge.failed_attempts = failed_attempts
    challenge.max_attempts = max_attempts
    challenge.admin_user_id = uuid.uuid4()
    return challenge


@pytest.mark.asyncio
async def test_create_invitation(dependencies):
    service = dependencies["service"]
    user_repository = dependencies["user_repository"]
    challenge_repository = dependencies["challenge_repository"]
    email_outbox_service = dependencies["email_outbox_service"]
    email_renderer = dependencies["email_renderer"]

    admin_user = make_admin_user()
    user_repository.get_by_id.return_value = admin_user

    result = await service.create_invitation(admin_user.id)

    assert isinstance(result, InvitationResultDTO)
    assert result.admin_user_id == admin_user.id
    assert result.email == admin_user.email
    assert result.invitation_token
    assert result.expires_at > datetime.now(UTC)

    user_repository.get_by_id.assert_awaited_once_with(
        admin_user.id,
        for_update=True,
    )

    challenge_repository.invalidate_pending_by_user_and_type.assert_awaited_once()
    challenge_repository.create.assert_called_once()

    challenge = challenge_repository.create.call_args.args[0]

    assert challenge.admin_user_id == admin_user.id
    assert challenge.challenge_type == ChallengeType.ACCOUNT_INVITATION
    assert challenge.challenge_token_hash == (f"hashed:{result.invitation_token}")
    assert challenge.max_attempts == 5

    email_renderer.render.assert_called_once()

    template_context = email_renderer.render.call_args.args[1]

    assert template_context["app_name"] == "Showroom"
    assert template_context["recipient_email"] == admin_user.email
    assert result.invitation_token in template_context["invitation_url"]
    assert template_context["expires_in_hours"] == 24

    email_outbox_service.enqueue.assert_awaited_once()

    enqueue_data = email_outbox_service.enqueue.call_args.args[0]

    assert isinstance(enqueue_data, EnqueueEmailDTO)
    assert enqueue_data.recipient == admin_user.email
    assert enqueue_data.subject == "You've been invited to Showroom"
    assert enqueue_data.html_content == "<p>Accept your invitation</p>"
    assert enqueue_data.text_content == "Accept your invitation"
    assert enqueue_data.idempotency_key.startswith(f"invitation:{admin_user.id}:")


@pytest.mark.asyncio
async def test_resend_invitation(dependencies):
    service = dependencies["service"]
    user_repository = dependencies["user_repository"]
    challenge_repository = dependencies["challenge_repository"]
    email_outbox_service = dependencies["email_outbox_service"]

    admin_user = make_admin_user()
    user_repository.get_by_id.return_value = admin_user

    result = await service.resend_invitation(admin_user.id)

    assert isinstance(result, InvitationResultDTO)
    assert result.admin_user_id == admin_user.id

    challenge_repository.invalidate_pending_by_user_and_type.assert_awaited_once()
    challenge_repository.create.assert_called_once()
    email_outbox_service.enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_invitation_email_enqueue_failure(dependencies):
    service = dependencies["service"]

    admin_user = make_admin_user()
    dependencies["user_repository"].get_by_id.return_value = admin_user
    dependencies["email_outbox_service"].enqueue.side_effect = RuntimeError(
        "Outbox unavailable"
    )

    with pytest.raises(RuntimeError, match="Outbox unavailable"):
        await service.create_invitation(admin_user.id)

    dependencies["challenge_repository"].create.assert_called_once()
    dependencies["uow"].commit.assert_not_called()


@pytest.mark.asyncio
async def test_validate_invitation(dependencies):
    service = dependencies["service"]
    user_repository = dependencies["user_repository"]
    challenge_repository = dependencies["challenge_repository"]

    admin_user = make_admin_user()
    challenge = make_challenge()
    challenge.admin_user_id = admin_user.id

    challenge_repository.get_by_token_hash.return_value = challenge
    user_repository.get_by_id.return_value = admin_user

    result = await service.validate_invitation("valid-token")

    assert isinstance(result, ValidateInvitationDTO)
    assert result.admin_user_id == admin_user.id
    assert result.email == admin_user.email
    assert result.expires_at == challenge.expires_at

    challenge_repository.get_by_token_hash.assert_awaited_once_with(
        "hashed:valid-token",
        ChallengeType.ACCOUNT_INVITATION,
    )


@pytest.mark.asyncio
async def test_validate_invitation_not_found(dependencies):
    dependencies["challenge_repository"].get_by_token_hash.return_value = None

    with pytest.raises(InvitationNotFoundError):
        await dependencies["service"].validate_invitation("invalid-token")


@pytest.mark.asyncio
async def test_validate_invitation_expired(dependencies):
    challenge = make_challenge(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge

    with pytest.raises(InvitationExpiredError):
        await dependencies["service"].validate_invitation("expired-token")


@pytest.mark.asyncio
async def test_validate_invitation_already_used(dependencies):
    challenge = make_challenge(consumed_at=datetime.now(UTC))
    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge

    with pytest.raises(InvitationAlreadyUsedError):
        await dependencies["service"].validate_invitation("used-token")


@pytest.mark.asyncio
async def test_validate_invitation_attempts_exceeded(dependencies):
    challenge = make_challenge(
        failed_attempts=5,
        max_attempts=5,
    )
    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge

    with pytest.raises(InvitationAttemptsExceededError):
        await dependencies["service"].validate_invitation("locked-token")


@pytest.mark.asyncio
async def test_validate_invitation_account_not_invited(dependencies):
    admin_user = make_admin_user(AdminUserStatus.DISABLED)
    challenge = make_challenge()
    challenge.admin_user_id = admin_user.id

    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge
    dependencies["user_repository"].get_by_id.return_value = admin_user

    with pytest.raises(InvitationNotFoundError):
        await dependencies["service"].validate_invitation("disabled-account-token")


@pytest.mark.asyncio
async def test_create_invitation_account_not_found(dependencies):
    dependencies["user_repository"].get_by_id.return_value = None

    with pytest.raises(AccountNotFoundError):
        await dependencies["service"].create_invitation(uuid.uuid4())


@pytest.mark.asyncio
async def test_create_invitation_account_not_eligible(dependencies):
    admin_user = make_admin_user(AdminUserStatus.ACTIVE)
    dependencies["user_repository"].get_by_id.return_value = admin_user

    with pytest.raises(AccountNotEligibleForInvitationError):
        await dependencies["service"].create_invitation(admin_user.id)


@pytest.mark.asyncio
async def test_revoke_invitation(dependencies):
    service = dependencies["service"]
    admin_user = make_admin_user()

    dependencies["user_repository"].get_by_id.return_value = admin_user

    await service.revoke_invitation(admin_user.id)

    assert admin_user.status == AdminUserStatus.DISABLED

    dependencies[
        "challenge_repository"
    ].invalidate_pending_by_user_and_type.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_invitation_account_not_found(dependencies):
    dependencies["user_repository"].get_by_id.return_value = None

    with pytest.raises(AccountNotFoundError):
        await dependencies["service"].revoke_invitation(uuid.uuid4())


@pytest.mark.asyncio
async def test_revoke_invitation_account_not_eligible(dependencies):
    admin_user = make_admin_user(AdminUserStatus.ACTIVE)
    dependencies["user_repository"].get_by_id.return_value = admin_user

    with pytest.raises(AccountNotEligibleForInvitationError):
        await dependencies["service"].revoke_invitation(admin_user.id)


def test_validate_challenge_valid(dependencies):
    challenge = make_challenge()

    dependencies["service"]._validate_challenge(
        challenge,
        datetime.now(UTC),
    )


def test_validate_challenge_expired(dependencies):
    challenge = make_challenge(expires_at=datetime.now(UTC) - timedelta(seconds=1))

    with pytest.raises(InvitationExpiredError):
        dependencies["service"]._validate_challenge(
            challenge,
            datetime.now(UTC),
        )
