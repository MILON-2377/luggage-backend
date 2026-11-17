import asyncio
import logging

import app.core.database.models
from app.core.database.seeders.system_roles import seed_system_roles
from app.core.database.session import AsyncSessionLocal
from app.core.database.unit_of_work import UnitOfWork
from app.modules.authentication.repositories.registry import (
    register_authentication_repositories,
)

logger = logging.getLogger(__name__)


async def run_seeders() -> None:
    async with AsyncSessionLocal() as session, UnitOfWork(session) as uow:
        register_authentication_repositories(uow)

        await seed_system_roles(uow)

        await uow.commit()


def main() -> None:
    try:
        asyncio.run(run_seeders())
        print("System roles seeded successfully.")

    except Exception:
        logger.exception("System role seeding failed.")
        raise


if __name__ == "__main__":
    main()
