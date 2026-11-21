import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.email.template_renderer import AbstractEmailTemplateRenderer
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories.admin_totp_credential import (
    AbstractAdminTotpCredentialRepository,
)
from app.modules.authentication.contracts.repositories.admin_user import (
    AbstractAdminUserRepository,
)
from app.modules.authentication.contracts.repositories.auth_challenge import (
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.services.initial_mfa_setup_resend import (
    AbstractInitialMFASetupResendService,
)
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.models import AuthChallenge
from app.modules.notification.contracts.services.email_outbox import (
    AbstractEmailOutboxService,
)
from app.modules.notification.dtos.email_outbox import EnqueueEmailDTO

INITIAL_MFA_SETUP_TOKEN_TTL = timedelta(minutes=30)
INITIAL_MFA_SETUP_MAX_ATTEMPTS = 5
INITIAL_MFA_SETUP_TEMPLATE = "initial_mfa_setup"


class InitialMFASetupResendService(AbstractInitialMFASetupResendService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        id_generator: AbstractIDGenerator,
        token_hasher: TokenHasher,
        email_outbox_service: AbstractEmailOutboxService,
        email_renderer: AbstractEmailTemplateRenderer,
        settings: Settings,
    ) -> None:
        self.uow = uow
        self.id_generator = id_generator
        self.token_hasher = token_hasher
        self.email_outbox_service = email_outbox_service
        self.email_renderer = email_renderer
        self.settings = settings

    async def resend(self, email: str) -> None:
        normalized_email = email.strip().lower()

        if not normalized_email:
            return

        now = datetime.now(UTC)

        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        totp_credential_repository = self.uow.get_repository(
            AbstractAdminTotpCredentialRepository
        )

        admin_user = await admin_user_repository.get_by_email(
            normalized_email,
            for_update=True,
        )

        if admin_user is None:
            return

        if admin_user.status != AdminUserStatus.PENDING_MFA_SETUP:
            return

        existing_credential = (
            await totp_credential_repository.get_active_by_admin_user_id(
                admin_user.id,
                for_update=True,
            )
        )

        if existing_credential is not None:
            return

        admin_user_id = admin_user.id

        await challenge_repository.invalidate_pending_by_user_and_type(
            admin_user_id,
            ChallengeType.INITIAL_MFA_SETUP,
            now,
        )

        await challenge_repository.invalidate_pending_by_user_and_type(
            admin_user_id,
            ChallengeType.MFA_ENROLLMENT_SESSION,
            now,
        )

        setup_token = secrets.token_urlsafe(32)
        challenge_id = self.id_generator.generate()

        challenge_repository.create(
            AuthChallenge(
                id=challenge_id,
                admin_user_id=admin_user_id,
                challenge_type=ChallengeType.INITIAL_MFA_SETUP,
                challenge_token_hash=self.token_hasher.hash_token(setup_token),
                challenge_data={
                    "purpose": "initial_super_admin_mfa_setup",
                },
                expires_at=now + INITIAL_MFA_SETUP_TOKEN_TTL,
                max_attempts=INITIAL_MFA_SETUP_MAX_ATTEMPTS,
            )
        )

        setup_url = (
            f"{self.settings.FRONTEND_BASE_URL.rstrip('/')}"
            f"/initial-mfa-setup"
            f"#token={quote(setup_token)}"
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
                idempotency_key=(
                    f"initial-mfa-setup-resend:{admin_user_id}:{challenge_id}"
                ),
            )
        )

        await self.uow.flush()
