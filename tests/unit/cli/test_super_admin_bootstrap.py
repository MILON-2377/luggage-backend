import hashlib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import app.modules.media.models
from app.cli.bootstrap.super_admin import SuperAdminBootstrapService
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.notification.dtos.email_outbox import EnqueueEmailDTO


@pytest.mark.asyncio
async def test_create_super_admin_enqueues_initial_mfa_setup_email() -> None:
    admin_user_repository = Mock()
    admin_user_repository.acquire_super_admin_bootstrap_lock = AsyncMock()
    admin_user_repository.has_super_admin = AsyncMock(return_value=False)
    admin_user_repository.get_by_email = AsyncMock(return_value=None)

    profile_repository = Mock()
    challenge_repository = Mock()
    role_repository = Mock()
    role_repository.get_by_slug = AsyncMock(
        return_value=SimpleNamespace(id=uuid.uuid4())
    )
    user_role_repository = Mock()

    repositories = {
        "admin_user": admin_user_repository,
        "profile": profile_repository,
        "challenge": challenge_repository,
        "role": role_repository,
        "user_role": user_role_repository,
    }

    repository_types = {
        "admin_user": __import__(
            "app.modules.authentication.contracts.repositories.admin_user",
            fromlist=["AbstractAdminUserRepository"],
        ).AbstractAdminUserRepository,
        "profile": __import__(
            "app.modules.authentication.contracts.repositories.admin_user_profile",
            fromlist=["AbstractAdminUserProfileRepository"],
        ).AbstractAdminUserProfileRepository,
        "challenge": __import__(
            "app.modules.authentication.contracts.repositories.auth_challenge",
            fromlist=["AbstractAuthChallengeRepository"],
        ).AbstractAuthChallengeRepository,
        "role": __import__(
            "app.modules.authentication.contracts.repositories.role",
            fromlist=["AbstractRoleRepository"],
        ).AbstractRoleRepository,
        "user_role": __import__(
            "app.modules.authentication.contracts.repositories.user_role",
            fromlist=["AbstractUserRoleRepository"],
        ).AbstractUserRoleRepository,
    }

    uow = Mock()
    uow.get_repository.side_effect = lambda repository_type: repositories[
        next(
            key
            for key, registered_type in repository_types.items()
            if repository_type is registered_type
        )
    ]
    uow.flush = AsyncMock()

    id_generator = Mock()
    id_generator.generate.side_effect = lambda: uuid.uuid4()

    password_hasher = Mock()
    password_hasher.hash_password.return_value = "hashed-password"

    token_hasher = Mock()
    token_hasher.hash_token.side_effect = lambda token: hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    email_outbox_service = Mock()
    email_outbox_service.enqueue = AsyncMock()

    email_renderer = Mock()
    email_renderer.render.return_value = SimpleNamespace(
        subject="Manufacturer Portal - Complete your initial MFA setup",
        html_content="<a>Complete MFA setup</a>",
        text_content="Complete MFA setup",
    )

    settings = SimpleNamespace(
        APP_NAME="Manufacturer Portal",
        FRONTEND_BASE_URL="https://example.com/",
    )

    service = SuperAdminBootstrapService(
        uow=uow,
        id_generator=id_generator,
        password_hasher=password_hasher,
        token_hasher=token_hasher,
        email_outbox_service=email_outbox_service,
        email_renderer=email_renderer,
        settings=settings,
    )

    result = await service.create_super_admin(
        email="  ADMIN@example.com  ",
        password="Strong-Password-2026!",
        first_name="Admin",
        last_name="User",
    )

    assert result.email == "admin@example.com"
    assert result.admin_user_id is not None
    assert result.initial_mfa_setup_token

    admin_user = admin_user_repository.create.call_args.args[0]
    assert admin_user.email == "admin@example.com"
    assert admin_user.status == AdminUserStatus.PENDING_MFA_SETUP

    challenge = challenge_repository.create.call_args.args[0]
    assert challenge.challenge_type == ChallengeType.INITIAL_MFA_SETUP
    assert (
        challenge.challenge_token_hash
        == hashlib.sha256(result.initial_mfa_setup_token.encode("utf-8")).hexdigest()
    )
    assert challenge.challenge_token_hash != result.initial_mfa_setup_token
    assert challenge.max_attempts == 5

    email_renderer.render.assert_called_once()
    template_name = email_renderer.render.call_args.kwargs["template_name"]
    context = email_renderer.render.call_args.kwargs["context"]

    assert template_name == "initial_mfa_setup"
    assert context["recipient_email"] == "admin@example.com"
    assert context["expires_in_minutes"] == 30
    assert context["setup_url"].startswith("https://example.com/dashboard#token=")
    assert result.initial_mfa_setup_token in context["setup_url"]

    email_outbox_service.enqueue.assert_awaited_once()

    email_dto = email_outbox_service.enqueue.call_args.args[0]
    assert isinstance(email_dto, EnqueueEmailDTO)
    assert email_dto.recipient == "admin@example.com"
    assert email_dto.subject == (
        "Manufacturer Portal - Complete your initial MFA setup"
    )
    assert email_dto.idempotency_key == (f"initial-mfa-setup:{result.admin_user_id}")

    admin_user_repository.acquire_super_admin_bootstrap_lock.assert_awaited_once()
    assert uow.flush.await_count == 2
