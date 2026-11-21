import asyncio
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from email_validator import EmailNotValidError, validate_email

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.email.template_renderer import AbstractEmailTemplateRenderer
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.password_hasher import PasswordHasher
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories.admin_user import (
    AbstractAdminUserRepository,
)
from app.modules.authentication.contracts.repositories.admin_user_profile import (
    AbstractAdminUserProfileRepository,
)
from app.modules.authentication.contracts.repositories.auth_challenge import (
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.repositories.role import (
    AbstractRoleRepository,
)
from app.modules.authentication.contracts.repositories.user_role import (
    AbstractUserRoleRepository,
)
from app.modules.authentication.enums import AdminUserStatus, ChallengeType, RoleType
from app.modules.authentication.models import (
    AdminUser,
    AdminUserProfile,
    AuthChallenge,
    UserRole,
)
from app.modules.notification.contracts.services.email_outbox import (
    AbstractEmailOutboxService,
)
from app.modules.notification.dtos.email_outbox import EnqueueEmailDTO

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
MAX_NAME_LENGTH = 100
MAX_DISPLAY_NAME_LENGTH = 150
MAX_EMAIL_LENGTH = 255
DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_LANGUAGE = "en"
INITIAL_MFA_SETUP_TOKEN_TTL = timedelta(minutes=30)
INITIAL_MFA_SETUP_TEMPLATE = "initial_mfa_setup"


@dataclass(frozen=True, slots=True)
class SuperAdminBootstrapResult:
    admin_user_id: uuid.UUID
    email: str
    initial_mfa_setup_token: str


class SuperAdminBootstrapService:
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        id_generator: AbstractIDGenerator,
        password_hasher: PasswordHasher,
        token_hasher: TokenHasher,
        email_outbox_service: AbstractEmailOutboxService,
        email_renderer: AbstractEmailTemplateRenderer,
        settings: Settings,
    ) -> None:
        self.uow = uow
        self.id_generator = id_generator
        self.password_hasher = password_hasher
        self.token_hasher = token_hasher
        self.email_outbox_service = email_outbox_service
        self.email_renderer = email_renderer
        self.settings = settings

    async def create_super_admin(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> SuperAdminBootstrapResult:
        normalized_email = self._normalize_email(email)
        self._validate_password(password, normalized_email)
        first_name = self._clean_name(first_name, "First name")
        last_name = self._clean_name(last_name, "Last name")

        password_hash = await asyncio.to_thread(
            self.password_hasher.hash_password,
            password,
        )

        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        profile_repository = self.uow.get_repository(AbstractAdminUserProfileRepository)
        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        role_repository = self.uow.get_repository(AbstractRoleRepository)
        user_role_repository = self.uow.get_repository(AbstractUserRoleRepository)

        await admin_user_repository.acquire_super_admin_bootstrap_lock()

        if await admin_user_repository.has_super_admin():
            raise RuntimeError(
                "A Super Admin already exists. Bootstrap is allowed only once."
            )

        if await admin_user_repository.get_by_email(normalized_email) is not None:
            raise ValueError("An account with this email address already exists.")

        super_admin_role = await role_repository.get_by_slug(RoleType.SUPER_ADMIN.value)

        if super_admin_role is None:
            raise RuntimeError(
                "The SUPER_ADMIN role does not exist. Seed system roles first."
            )

        now = datetime.now(UTC)
        admin_user_id = self.id_generator.generate()

        initial_mfa_setup_token = secrets.token_urlsafe(32)
        initial_mfa_setup_token_hash = self.token_hasher.hash_token(
            initial_mfa_setup_token
        )

        admin_user_repository.create(
            AdminUser(
                id=admin_user_id,
                email=normalized_email,
                password_hash=password_hash,
                status=AdminUserStatus.PENDING_MFA_SETUP,
                email_verified_at=now,
                password_changed_at=now,
            )
        )

        await self.uow.flush()

        profile_repository.create(
            AdminUserProfile(
                id=self.id_generator.generate(),
                admin_user_id=admin_user_id,
                first_name=first_name,
                last_name=last_name,
                display_name=(f"{first_name} {last_name}"[:MAX_DISPLAY_NAME_LENGTH]),
                timezone=DEFAULT_TIMEZONE,
                language=DEFAULT_LANGUAGE,
            )
        )

        user_role_repository.create(
            UserRole(
                admin_user_id=admin_user_id,
                role_id=super_admin_role.id,
                assigned_by=None,
            )
        )

        challenge_repository.create(
            AuthChallenge(
                id=self.id_generator.generate(),
                admin_user_id=admin_user_id,
                challenge_type=ChallengeType.INITIAL_MFA_SETUP,
                challenge_token_hash=initial_mfa_setup_token_hash,
                challenge_data={
                    "purpose": "initial_super_admin_mfa_setup",
                },
                expires_at=now + INITIAL_MFA_SETUP_TOKEN_TTL,
                max_attempts=5,
            )
        )

        setup_url = (
            f"{self.settings.FRONTEND_BASE_URL.rstrip('/')}"
            f"/initial-mfa-setup"
            f"#token={quote(initial_mfa_setup_token)}"
        )

        rendered_email = self.email_renderer.render(
            template_name=INITIAL_MFA_SETUP_TEMPLATE,
            context={
                "app_name": self.settings.APP_NAME,
                "setup_url": setup_url,
                "recipient_email": normalized_email,
                "expires_in_minutes": int(
                    INITIAL_MFA_SETUP_TOKEN_TTL.total_seconds() // 60
                ),
            },
        )

        await self.email_outbox_service.enqueue(
            EnqueueEmailDTO(
                recipient=normalized_email,
                subject=rendered_email.subject,
                html_content=rendered_email.html_content,
                text_content=rendered_email.text_content,
                idempotency_key=f"initial-mfa-setup:{admin_user_id}",
            )
        )

        await self.uow.flush()

        return SuperAdminBootstrapResult(
            admin_user_id=admin_user_id,
            email=normalized_email,
            initial_mfa_setup_token=initial_mfa_setup_token,
        )

    @staticmethod
    def _normalize_email(email: str) -> str:
        try:
            result = validate_email(
                email.strip(),
                check_deliverability=False,
            )
        except EmailNotValidError as exc:
            raise ValueError("Invalid email address.") from exc

        normalized = result.normalized.lower()

        if len(normalized) > MAX_EMAIL_LENGTH:
            raise ValueError("Email address is too long.")

        return normalized

    @staticmethod
    def _clean_name(value: str, label: str) -> str:
        cleaned = " ".join(value.split())

        if not cleaned:
            raise ValueError(f"{label} is required.")

        if len(cleaned) > MAX_NAME_LENGTH:
            raise ValueError(f"{label} must not exceed {MAX_NAME_LENGTH} characters.")

        return cleaned

    @staticmethod
    def _validate_password(password: str, email: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must contain at least {MIN_PASSWORD_LENGTH} characters."
            )

        if len(password) > MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must not exceed {MAX_PASSWORD_LENGTH} characters."
            )

        if len(password.encode("utf-8")) > 1024:
            raise ValueError("Password is too long.")

        if not password.strip():
            raise ValueError("Password must not be blank.")

        if password.lower() == email.lower():
            raise ValueError("Password must not be the same as the email address.")
