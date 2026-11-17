import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from email_validator import EmailNotValidError, validate_email

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.password_hasher import PasswordHasher
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
from app.modules.authentication.enums import AdminUserStatus, RoleType
from app.modules.authentication.models import AdminUser, AdminUserProfile, UserRole

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
MAX_NAME_LENGTH = 100
MAX_DISPLAY_NAME_LENGTH = 150
MAX_EMAIL_LENGTH = 255
DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_LANGUAGE = "en"


@dataclass(frozen=True, slots=True)
class SuperAdminBootstrapResult:
    admin_user_id: uuid.UUID
    email: str


class SuperAdminBootstrapService:
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        id_generator: AbstractIDGenerator,
        password_hasher: PasswordHasher,
    ) -> None:
        self.uow = uow
        self.id_generator = id_generator
        self.password_hasher = password_hasher

    async def create_super_admin(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> SuperAdminBootstrapResult:
        # Validate everything before touching the database.
        normalized_email = self._normalize_email(email)
        self._validate_password(password, normalized_email)
        first_name = self._clean_name(first_name, "First name")
        last_name = self._clean_name(last_name, "Last name")

        # Hash before taking the advisory lock: argon2 is slow and CPU-bound,
        # so it must neither hold the lock nor block the event loop.
        password_hash = await asyncio.to_thread(
            self.password_hasher.hash_password,
            password,
        )

        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        profile_repository = self.uow.get_repository(AbstractAdminUserProfileRepository)
        role_repository = self.uow.get_repository(AbstractRoleRepository)
        user_role_repository = self.uow.get_repository(AbstractUserRoleRepository)

        # Serialize concurrent bootstrap attempts (released on commit/rollback).
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
        role_id = super_admin_role.id

        admin_user_repository.create(
            AdminUser(
                id=admin_user_id,
                email=normalized_email,
                password_hash=password_hash,
                status=AdminUserStatus.ACTIVE,
                email_verified_at=now,
                password_changed_at=now,
            )
        )

        # Flush the user first so the FK targets exist for the rows below.
        await self.uow.flush()

        profile_repository.create(
            AdminUserProfile(
                id=self.id_generator.generate(),
                admin_user_id=admin_user_id,
                first_name=first_name,
                last_name=last_name,
                display_name=f"{first_name} {last_name}"[:MAX_DISPLAY_NAME_LENGTH],
                timezone=DEFAULT_TIMEZONE,
                language=DEFAULT_LANGUAGE,
            )
        )

        user_role_repository.create(
            UserRole(
                admin_user_id=admin_user_id,
                role_id=role_id,
                assigned_by=None,
            )
        )

        await self.uow.flush()

        return SuperAdminBootstrapResult(
            admin_user_id=admin_user_id,
            email=normalized_email,
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

        if not password.strip():
            raise ValueError("Password must not be blank.")

        if password.lower() == email.lower():
            raise ValueError("Password must not be the same as the email address.")
