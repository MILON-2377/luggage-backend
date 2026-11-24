import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.email.template_renderer import (
    AbstractEmailTemplateRenderer,
)
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories.admin_user import (
    AbstractAdminUserRepository,
)
from app.modules.authentication.contracts.repositories.auth_challenge import (
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.services.forgot_password import (
    AbstractForgotPasswordService,
)
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.models import AuthChallenge
from app.modules.notification.contracts.services.email_outbox import (
    AbstractEmailOutboxService,
)
from app.modules.notification.dtos.email_outbox import EnqueueEmailDTO

PASSWORD_RESET_EMAIL_TEMPLATE = "password_reset"


class ForgotPasswordService(AbstractForgotPasswordService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        token_hasher: TokenHasher,
        id_generator: AbstractIDGenerator,
        email_outbox_service: AbstractEmailOutboxService,
        email_renderer: AbstractEmailTemplateRenderer,
        settings: Settings,
    ) -> None:
        self.uow = uow
        self.token_hasher = token_hasher
        self.id_generator = id_generator
        self.email_outbox_service = email_outbox_service
        self.email_renderer = email_renderer
        self.settings = settings

    async def request_password_reset(self, email: str) -> None:
        user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)

        normalized_email = email.strip().lower()
        admin_user = await user_repository.get_by_email(
            normalized_email,
            for_update=True,
        )

        if admin_user is None or admin_user.status != AdminUserStatus.ACTIVE:
            return

        now = datetime.now(UTC)

        await challenge_repository.invalidate_pending_by_user_and_type(
            admin_user.id,
            ChallengeType.PASSWORD_RESET,
            now,
        )

        token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(
            minutes=self.settings.PASSWORD_RESET_EXPIRE_MINUTES
        )

        challenge_repository.create(
            AuthChallenge(
                id=self.id_generator.generate(),
                admin_user_id=admin_user.id,
                challenge_type=ChallengeType.PASSWORD_RESET,
                challenge_token_hash=self.token_hasher.hash_token(token),
                challenge_data={},
                expires_at=expires_at,
                max_attempts=self.settings.PASSWORD_RESET_MAX_ATTEMPTS,
            )
        )

        reset_url = (
            f"{self.settings.FRONTEND_BASE_URL.rstrip('/')}"
            f"{self.settings.PASSWORD_RESET_PATH}"
            f"?{urlencode({'token': token})}"
        )

        rendered = self.email_renderer.render(
            PASSWORD_RESET_EMAIL_TEMPLATE,
            {
                "app_name": self.settings.APP_NAME,
                "reset_url": reset_url,
                "recipient_email": admin_user.email,
                "expires_in_minutes": self.settings.PASSWORD_RESET_EXPIRE_MINUTES,
            },
        )

        await self.email_outbox_service.enqueue(
            EnqueueEmailDTO(
                recipient=admin_user.email,
                subject=rendered.subject,
                html_content=rendered.html_content,
                text_content=rendered.text_content,
                idempotency_key=(
                    f"password-reset:{admin_user.id}:{expires_at.isoformat()}"
                ),
            )
        )
