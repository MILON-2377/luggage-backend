from unittest.mock import MagicMock

import pytest

from app.core.database.unit_of_work import UnitOfWork
from app.modules.authentication.contracts.repositories import (
    AbstractAdminUserRepository,
    AbstractAuthChallengeRepository,
    AbstractRoleRepository,
)


@pytest.fixture
def uow():
    session = MagicMock()
    return UnitOfWork(session)


def test_register_authentication_repositories(uow):
    from app.modules.authentication.repositories.registry import (
        register_authentication_repositories,
    )

    register_authentication_repositories(uow)

    assert isinstance(
        uow.get_repository(AbstractAdminUserRepository),
        AbstractAdminUserRepository,
    )
    assert isinstance(
        uow.get_repository(AbstractAuthChallengeRepository),
        AbstractAuthChallengeRepository,
    )
    assert isinstance(
        uow.get_repository(AbstractRoleRepository),
        AbstractRoleRepository,
    )


def test_register_authentication_repositories_uses_same_session(uow):
    from app.modules.authentication.repositories.registry import (
        register_authentication_repositories,
    )

    register_authentication_repositories(uow)

    for repository in uow._repositories.values():
        assert repository.session is uow.session


def test_register_authentication_repositories_rejects_duplicates(uow):
    from app.modules.authentication.repositories.registry import (
        register_authentication_repositories,
    )

    register_authentication_repositories(uow)

    with pytest.raises(ValueError, match="already registered"):
        register_authentication_repositories(uow)
