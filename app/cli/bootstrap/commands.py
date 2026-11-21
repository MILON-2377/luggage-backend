import argparse
import asyncio
import logging
import sys
from getpass import getpass

import app.core.database.models
from app.cli.bootstrap.super_admin import SuperAdminBootstrapService
from app.core.config import settings
from app.core.database.session import AsyncSessionLocal
from app.core.database.unit_of_work import UnitOfWork
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.security.argon2_password_hasher import Argon2PasswordHasher
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.modules.authentication.repositories.registry import (
    register_authentication_repositories,
)
from app.modules.notification.dependencies.email_outbox import (
    get_email_outbox_service,
)
from app.modules.notification.dependencies.email_renderer import (
    get_email_renderer,
)
from app.modules.notification.repositories.registry import (
    register_notification_repositories,
)

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the initial Super Admin.")
    parser.add_argument("--email")
    parser.add_argument("--first-name")
    parser.add_argument("--last-name")
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the password from stdin (for non-interactive environments).",
    )
    return parser.parse_args()


def _require(value: str | None, prompt: str) -> str:
    value = (value or input(prompt)).strip()

    if not value:
        raise ValueError(f"{prompt.rstrip(': ')} is required.")

    return value


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
    else:
        password = getpass("Initial password: ")
        confirmation = getpass("Confirm password: ")

        if password != confirmation:
            raise ValueError("Passwords do not match.")

    if not password:
        raise ValueError("Password is required.")

    return password


async def bootstrap_super_admin(
    *,
    email: str,
    first_name: str,
    last_name: str,
    password: str,
) -> None:
    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session) as uow:
            register_authentication_repositories(uow)
            register_notification_repositories(uow)

            service = SuperAdminBootstrapService(
                uow=uow,
                id_generator=UUIDGenerator(),
                password_hasher=Argon2PasswordHasher(),
                token_hasher=SHA256TokenHasher(),
                email_outbox_service=get_email_outbox_service(uow),
                email_renderer=get_email_renderer(),
                settings=settings,
            )

            result = await service.create_super_admin(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            await uow.commit()

    print("\nSuper Admin created successfully.")
    print(f"User ID: {result.admin_user_id}")
    print(f"Email: {result.email}")
    print("\nInitial MFA setup email queued successfully.")
    print("The setup token is not displayed in the terminal.")


def main() -> None:
    args = _parse_args()

    try:
        print("\n=== Super Admin Bootstrap ===\n")

        email = _require(args.email, "Email: ")
        first_name = _require(args.first_name, "First name: ")
        last_name = _require(args.last_name, "Last name: ")
        password = _read_password(args.password_stdin)

        asyncio.run(
            bootstrap_super_admin(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
            )
        )
    except (KeyboardInterrupt, EOFError):
        print("\nBootstrap cancelled.")
        raise SystemExit(130) from None
    except (ValueError, RuntimeError) as exc:
        print(f"\nBootstrap failed: {exc}")
        raise SystemExit(1) from exc
    except Exception:
        logger.exception("Super Admin bootstrap failed unexpectedly")
        print("\nBootstrap failed due to an unexpected error. See logs for details.")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
