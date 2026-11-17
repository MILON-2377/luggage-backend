import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.email.template_renderer import (
    AbstractEmailTemplateRenderer,
)
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories import (
    AbstractAdminUserRepository,
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.services.invitation import (
    AbstractInvitationService,
)
from app.modules.authentication.dtos.invitation import InvitationResultDTO
from app.modules.authentication.dtos.validate_invitation import ValidateInvitationDTO
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.errors.invitation import (
    AccountNotEligibleForInvitationError,
    AccountNotFoundError,
    InvitationAlreadyUsedError,
    InvitationAttemptsExceededError,
    InvitationExpiredError,
    InvitationNotFoundError,
)
from app.modules.authentication.models import AdminUser, AuthChallenge
from app.modules.notification.contracts.services.email_outbox import (
    AbstractEmailOutboxService,
)
from app.modules.notification.dtos.email_outbox import EnqueueEmailDTO

INVITATION_EMAIL_TEMPLATE = "account_invitation"


class InvitationService(AbstractInvitationService):
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

    async def create_invitation(
        self,
        admin_user_id: uuid.UUID,
    ) -> InvitationResultDTO:
        return await self._issue_invitation(admin_user_id)

    async def resend_invitation(
        self,
        admin_user_id: uuid.UUID,
    ) -> InvitationResultDTO:
        return await self._issue_invitation(admin_user_id)

    async def validate_invitation(
        self,
        token: str,
    ) -> ValidateInvitationDTO:
        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        user_repository = self.uow.get_repository(AbstractAdminUserRepository)

        challenge = await challenge_repository.get_by_token_hash(
            self.token_hasher.hash_token(token),
            ChallengeType.ACCOUNT_INVITATION,
        )

        if challenge is None:
            raise InvitationNotFoundError

        self._validate_challenge(challenge, datetime.now(UTC))

        admin_user = await user_repository.get_by_id(challenge.admin_user_id)

        if admin_user is None or admin_user.status != AdminUserStatus.INVITED:
            raise InvitationNotFoundError

        return ValidateInvitationDTO(
            admin_user_id=admin_user.id,
            email=admin_user.email,
            expires_at=challenge.expires_at,
        )

    async def revoke_invitation(
        self,
        admin_user_id: uuid.UUID,
    ) -> None:
        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)

        admin_user = await self._get_invitable_user(admin_user_id)
        admin_user.status = AdminUserStatus.DISABLED

        await challenge_repository.invalidate_pending_by_user_and_type(
            admin_user.id,
            ChallengeType.ACCOUNT_INVITATION,
            datetime.now(UTC),
        )

    async def _issue_invitation(
        self,
        admin_user_id: uuid.UUID,
    ) -> InvitationResultDTO:
        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)

        admin_user = await self._get_invitable_user(admin_user_id)

        now = datetime.now(UTC)

        await challenge_repository.invalidate_pending_by_user_and_type(
            admin_user.id,
            ChallengeType.ACCOUNT_INVITATION,
            now,
        )

        token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(hours=self.settings.INVITATION_EXPIRE_HOURS)

        challenge_repository.create(
            AuthChallenge(
                id=self.id_generator.generate(),
                admin_user_id=admin_user.id,
                challenge_type=ChallengeType.ACCOUNT_INVITATION,
                challenge_token_hash=self.token_hasher.hash_token(token),
                challenge_data={},
                expires_at=expires_at,
                max_attempts=self.settings.INVITATION_MAX_ATTEMPTS,
            )
        )

        email = admin_user.email
        admin_id = admin_user.id

        invitation_url = (
            f"{self.settings.FRONTEND_BASE_URL.rstrip('/')}"
            f"{self.settings.INVITATION_ACCEPTANCE_PATH}"
            f"?{urlencode({'token': token})}"
        )

        rendered = self.email_renderer.render(
            INVITATION_EMAIL_TEMPLATE,
            {
                "app_name": self.settings.APP_NAME,
                "invitation_url": invitation_url,
                "recipient_email": email,
                "expires_in_hours": self.settings.INVITATION_EXPIRE_HOURS,
            },
        )

        await self.email_outbox_service.enqueue(
            EnqueueEmailDTO(
                recipient=email,
                subject=rendered.subject,
                html_content=rendered.html_content,
                text_content=rendered.text_content,
                idempotency_key=f"invitation:{admin_id}:{expires_at.isoformat()}",
            )
        )

        return InvitationResultDTO(
            admin_user_id=admin_id,
            email=email,
            invitation_token=token,
            expires_at=expires_at,
        )

    async def _get_invitable_user(
        self,
        admin_user_id: uuid.UUID,
    ) -> AdminUser:
        user_repository = self.uow.get_repository(AbstractAdminUserRepository)

        admin_user = await user_repository.get_by_id(
            admin_user_id,
            for_update=True,
        )

        if admin_user is None:
            raise AccountNotFoundError

        if admin_user.status != AdminUserStatus.INVITED:
            raise AccountNotEligibleForInvitationError

        return admin_user

    @staticmethod
    def _validate_challenge(
        challenge: AuthChallenge,
        now: datetime,
    ) -> None:
        if challenge.consumed_at is not None:
            raise InvitationAlreadyUsedError

        if challenge.expires_at <= now:
            raise InvitationExpiredError

        if challenge.failed_attempts >= challenge.max_attempts:
            raise InvitationAttemptsExceededError
