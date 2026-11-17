from enum import StrEnum


class RoleType(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    STAFF = "staff"

    @classmethod
    def provisionable(cls) -> frozenset["RoleType"]:
        return frozenset({cls.ADMIN, cls.STAFF})
