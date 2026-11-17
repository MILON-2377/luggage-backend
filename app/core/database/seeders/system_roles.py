from uuid import uuid4

from app.modules.authentication.contracts.repositories import (
    AbstractRoleRepository,
)
from app.modules.authentication.enums import RoleType
from app.modules.authentication.models import Role

SYSTEM_ROLES = (
    {
        "name": "Super Admin",
        "slug": RoleType.SUPER_ADMIN.value,
        "description": "Full access to all administrative capabilities.",
        "is_system_role": True,
    },
    {
        "name": "Admin",
        "slug": RoleType.ADMIN.value,
        "description": "Administrative access to permitted management capabilities.",
        "is_system_role": True,
    },
    {
        "name": "Staff",
        "slug": RoleType.STAFF.value,
        "description": "Staff access to assigned operational capabilities.",
        "is_system_role": True,
    },
)


async def seed_system_roles(uow) -> None:
    role_repository = uow.get_repository(AbstractRoleRepository)

    for role_data in SYSTEM_ROLES:
        existing_role = await role_repository.get_by_slug(role_data["slug"])

        if existing_role is not None:
            continue

        role_repository.create(
            Role(
                id=uuid4(),
                **role_data,
            )
        )

    await uow.flush()
