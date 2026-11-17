import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors.base import ValidationError
from app.modules.authentication.dtos.accept_invitation import AcceptInvitationDTO
from app.modules.authentication.enums.admin_user_status import AdminUserStatus
from app.modules.authentication.enums.challenge_type import ChallengeType
from app.modules.authentication.errors import (
    AccountNotEligibleForInvitationError,
    InvitationAlreadyUsedError,
    InvitationAttemptsExceededError,
    InvitationExpiredError,
    InvitationNotFoundError,
)
from app.modules.authentication.models.admin_user import AdminUser
from app.modules.authentication.models.admin_user_profile import AdminUserProfile
from app.modules.authentication.models.auth_challenge import AuthChallenge
from app.modules.authentication.services.invitation_acceptance import (
    InvitationAcceptanceService,
)


@pytest.fixture
def dependencies():
    uow = MagicMock()
    uow.flush = AsyncMock()
    uow.commit = AsyncMock()

    token_hasher = MagicMock()
    token_hasher.hash_token.side_effect = lambda token: f"hashed:{token}"

    password_hasher = MagicMock()
    password_hasher.hash_password.side_effect = lambda password: f"hash:{password}"

    user_repository = AsyncMock()
    challenge_repository = AsyncMock()
    profile_repository = AsyncMock()

    challenge_repository.consume.return_value = True

    uow.get_repository.side_effect = lambda repository_type: {
        "AbstractAdminUserRepository": user_repository,
        "AbstractAuthChallengeRepository": challenge_repository,
        "AbstractAdminUserProfileRepository": profile_repository,
    }[repository_type.__name__]

    service = InvitationAcceptanceService(
        uow=uow,
        token_hasher=token_hasher,
        password_hasher=password_hasher,
    )

    return {
        "service": service,
        "uow": uow,
        "token_hasher": token_hasher,
        "password_hasher": password_hasher,
        "user_repository": user_repository,
        "challenge_repository": challenge_repository,
        "profile_repository": profile_repository,
    }


def make_admin_user(
    status: AdminUserStatus = AdminUserStatus.INVITED,
    password_hash: str | None = None,
) -> MagicMock:
    user = MagicMock(spec=AdminUser)
    user.id = uuid.uuid4()
    user.email = "employee@example.com"
    user.status = status
    user.password_hash = password_hash
    user.password_changed_at = None
    user.email_verified_at = None
    return user


def make_challenge(
    *,
    consumed_at: datetime | None = None,
    expires_at: datetime | None = None,
    failed_attempts: int = 0,
    max_attempts: int = 5,
) -> MagicMock:
    challenge = MagicMock(spec=AuthChallenge)
    challenge.id = uuid.uuid4()
    challenge.consumed_at = consumed_at
    challenge.expires_at = expires_at or (datetime.now(UTC) + timedelta(hours=1))
    challenge.failed_attempts = failed_attempts
    challenge.max_attempts = max_attempts
    challenge.admin_user_id = uuid.uuid4()
    return challenge


def make_profile() -> MagicMock:
    profile = MagicMock(spec=AdminUserProfile)
    profile.timezone = "Asia/Shanghai"
    profile.language = "en"
    return profile


def make_dto(**overrides) -> AcceptInvitationDTO:
    values = {
        "invitation_token": "valid-token",
        "password": "Str0ng-Passw0rd!",
        "first_name": "  Jane  ",
        "last_name": "  Doe  ",
        "display_name": "  Jane D.  ",
        "phone": "+8613800138000",
        "job_title": "Engineer",
        "department": "Sales",
        "timezone": "Europe/Berlin",
        "language": "de",
    }
    values.update(overrides)
    return AcceptInvitationDTO(**values)


def setup_happy_path(dependencies):
    admin_user = make_admin_user()
    challenge = make_challenge()
    challenge.admin_user_id = admin_user.id
    profile = make_profile()

    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge
    dependencies["user_repository"].get_by_id.return_value = admin_user
    dependencies["profile_repository"].get_by_admin_user_id.return_value = profile

    return admin_user, challenge, profile


@pytest.mark.asyncio
async def test_accept_invitation_success(dependencies):
    admin_user, challenge, profile = setup_happy_path(dependencies)
    before = datetime.now(UTC)

    await dependencies["service"].accept_invitation(make_dto())

    dependencies["challenge_repository"].get_by_token_hash.assert_awaited_once_with(
        "hashed:valid-token",
        ChallengeType.ACCOUNT_INVITATION,
        for_update=True,
    )
    dependencies["user_repository"].get_by_id.assert_awaited_once_with(
        challenge.admin_user_id,
        for_update=True,
    )
    dependencies["profile_repository"].get_by_admin_user_id.assert_awaited_once_with(
        admin_user.id
    )

    dependencies["challenge_repository"].consume.assert_awaited_once()
    consume_args = dependencies["challenge_repository"].consume.call_args.args
    assert consume_args[0] == challenge.id
    assert consume_args[1] >= before

    assert admin_user.password_hash == "hash:Str0ng-Passw0rd!"
    assert admin_user.status == AdminUserStatus.ACTIVE
    assert admin_user.password_changed_at >= before
    assert admin_user.email_verified_at >= before

    assert profile.first_name == "Jane"
    assert profile.last_name == "Doe"
    assert profile.display_name == "Jane D."
    assert profile.phone == "+8613800138000"
    assert profile.job_title == "Engineer"
    assert profile.department == "Sales"
    assert profile.timezone == "Europe/Berlin"
    assert profile.language == "de"

    dependencies["uow"].flush.assert_awaited_once()
    dependencies["uow"].commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_accept_invitation_blank_optionals_become_none(dependencies):
    _, _, profile = setup_happy_path(dependencies)

    await dependencies["service"].accept_invitation(
        make_dto(
            display_name="   ",
            phone="",
            job_title=" ",
            department=None,
        )
    )

    assert profile.display_name is None
    assert profile.phone is None
    assert profile.job_title is None
    assert profile.department is None


@pytest.mark.asyncio
async def test_accept_invitation_keeps_default_timezone_and_language(dependencies):
    _, _, profile = setup_happy_path(dependencies)

    await dependencies["service"].accept_invitation(
        make_dto(timezone=None, language="  ")
    )

    assert profile.timezone == "Asia/Shanghai"
    assert profile.language == "en"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"first_name": ""},
        {"first_name": "   "},
        {"last_name": ""},
        {"last_name": "   "},
    ],
)
async def test_accept_invitation_requires_names(dependencies, overrides):
    with pytest.raises(ValidationError):
        await dependencies["service"].accept_invitation(make_dto(**overrides))

    dependencies["challenge_repository"].get_by_token_hash.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_invitation_requires_password(dependencies):
    with pytest.raises(ValidationError):
        await dependencies["service"].accept_invitation(make_dto(password=""))

    dependencies["password_hasher"].hash_password.assert_not_called()
    dependencies["challenge_repository"].get_by_token_hash.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_invitation_not_found(dependencies):
    dependencies["challenge_repository"].get_by_token_hash.return_value = None

    with pytest.raises(InvitationNotFoundError):
        await dependencies["service"].accept_invitation(make_dto())

    dependencies["user_repository"].get_by_id.assert_not_awaited()
    dependencies["challenge_repository"].consume.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_invitation_expired(dependencies):
    challenge = make_challenge(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge

    with pytest.raises(InvitationExpiredError):
        await dependencies["service"].accept_invitation(make_dto())

    dependencies["challenge_repository"].consume.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_invitation_already_used(dependencies):
    challenge = make_challenge(consumed_at=datetime.now(UTC))
    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge

    with pytest.raises(InvitationAlreadyUsedError):
        await dependencies["service"].accept_invitation(make_dto())

    dependencies["challenge_repository"].consume.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_invitation_attempts_exceeded(dependencies):
    challenge = make_challenge(failed_attempts=5, max_attempts=5)
    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge

    with pytest.raises(InvitationAttemptsExceededError):
        await dependencies["service"].accept_invitation(make_dto())

    dependencies["challenge_repository"].consume.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_invitation_account_not_found(dependencies):
    dependencies[
        "challenge_repository"
    ].get_by_token_hash.return_value = make_challenge()
    dependencies["user_repository"].get_by_id.return_value = None

    with pytest.raises(AccountNotEligibleForInvitationError):
        await dependencies["service"].accept_invitation(make_dto())

    dependencies["challenge_repository"].consume.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "password_hash"),
    [
        (AdminUserStatus.ACTIVE, None),
        (AdminUserStatus.DISABLED, None),
        (AdminUserStatus.SUSPENDED, None),
        (AdminUserStatus.INVITED, "existing-hash"),
    ],
)
async def test_accept_invitation_account_not_eligible(
    dependencies, status, password_hash
):
    admin_user = make_admin_user(status=status, password_hash=password_hash)
    challenge = make_challenge()
    challenge.admin_user_id = admin_user.id

    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge
    dependencies["user_repository"].get_by_id.return_value = admin_user

    with pytest.raises(AccountNotEligibleForInvitationError):
        await dependencies["service"].accept_invitation(make_dto())

    dependencies["challenge_repository"].consume.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()
    assert admin_user.status == status


@pytest.mark.asyncio
async def test_accept_invitation_profile_missing(dependencies):
    admin_user = make_admin_user()
    challenge = make_challenge()
    challenge.admin_user_id = admin_user.id

    dependencies["challenge_repository"].get_by_token_hash.return_value = challenge
    dependencies["user_repository"].get_by_id.return_value = admin_user
    dependencies["profile_repository"].get_by_admin_user_id.return_value = None

    with pytest.raises(AccountNotEligibleForInvitationError):
        await dependencies["service"].accept_invitation(make_dto())

    dependencies["challenge_repository"].consume.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()
    assert admin_user.password_hash is None


@pytest.mark.asyncio
async def test_accept_invitation_lost_consume_race(dependencies):
    admin_user, _, profile = setup_happy_path(dependencies)
    dependencies["challenge_repository"].consume.return_value = False

    with pytest.raises(InvitationAlreadyUsedError):
        await dependencies["service"].accept_invitation(make_dto())

    assert admin_user.password_hash is None
    assert admin_user.status == AdminUserStatus.INVITED
    assert profile.first_name != "Jane"
    dependencies["uow"].flush.assert_not_awaited()
    dependencies["uow"].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_invitation_hashes_password_once(dependencies):
    setup_happy_path(dependencies)

    await dependencies["service"].accept_invitation(make_dto())

    dependencies["password_hasher"].hash_password.assert_called_once_with(
        "Str0ng-Passw0rd!"
    )


@pytest.mark.asyncio
async def test_accept_invitation_flush_failure_does_not_commit(dependencies):
    setup_happy_path(dependencies)
    dependencies["uow"].flush.side_effect = RuntimeError("Flush failed")

    with pytest.raises(RuntimeError, match="Flush failed"):
        await dependencies["service"].accept_invitation(make_dto())

    dependencies["uow"].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_invitation_commit_failure_propagates(dependencies):
    setup_happy_path(dependencies)
    dependencies["uow"].commit.side_effect = RuntimeError("Commit failed")

    with pytest.raises(RuntimeError, match="Commit failed"):
        await dependencies["service"].accept_invitation(make_dto())


def test_validate_challenge_valid(dependencies):
    dependencies["service"]._validate_challenge(make_challenge(), datetime.now(UTC))


def test_validate_challenge_expired(dependencies):
    challenge = make_challenge(expires_at=datetime.now(UTC) - timedelta(seconds=1))

    with pytest.raises(InvitationExpiredError):
        dependencies["service"]._validate_challenge(challenge, datetime.now(UTC))


def test_validate_challenge_already_used(dependencies):
    challenge = make_challenge(consumed_at=datetime.now(UTC))

    with pytest.raises(InvitationAlreadyUsedError):
        dependencies["service"]._validate_challenge(challenge, datetime.now(UTC))


def test_validate_challenge_attempts_exceeded(dependencies):
    challenge = make_challenge(failed_attempts=5, max_attempts=5)

    with pytest.raises(InvitationAttemptsExceededError):
        dependencies["service"]._validate_challenge(challenge, datetime.now(UTC))
