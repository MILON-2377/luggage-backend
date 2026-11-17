from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.database.unit_of_work import UnitOfWork
from app.modules.authentication.contracts.repositories import (
    AbstractAdminUserRepository,
)


@pytest.fixture
def session():
    mock = MagicMock()
    mock.in_transaction.return_value = False
    mock.begin = AsyncMock()
    mock.flush = AsyncMock()
    mock.refresh = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_unit_of_work_begins_transaction(session):
    uow = UnitOfWork(session)

    async with uow:
        assert uow._entered is True
        await uow.commit()

    session.begin.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_unit_of_work_rollbacks_on_exception(session):
    uow = UnitOfWork(session)

    with pytest.raises(ValueError, match="test error"):
        async with uow:
            raise ValueError("test error")

    session.begin.assert_awaited_once()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_unit_of_work_rejects_reentrant_entry(session):
    uow = UnitOfWork(session)

    async with uow:
        with pytest.raises(RuntimeError, match="not re-entrant"):
            await uow.__aenter__()


@pytest.mark.asyncio
async def test_unit_of_work_clears_repositories_after_exit(session):
    uow = UnitOfWork(session)

    async with uow:
        assert uow._repositories == {}

    assert uow._repositories == {}


def test_get_repository_rejects_unregistered_repository(session):
    uow = UnitOfWork(session)

    with pytest.raises(LookupError, match="not registered"):
        uow.get_repository(AbstractAdminUserRepository)