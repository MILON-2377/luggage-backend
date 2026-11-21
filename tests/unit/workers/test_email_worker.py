import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.email.email_worker import run_email_worker


@pytest.mark.asyncio
async def test_worker_stops_without_polling_when_stop_event_is_set():
    stop_event = asyncio.Event()
    stop_event.set()

    http_client = MagicMock()
    http_client.__aenter__ = AsyncMock(return_value=http_client)
    http_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.workers.email.email_worker.AsyncClient",
        return_value=http_client,
    ) as async_client:
        with patch(
            "app.workers.email.email_worker.AsyncSessionLocal"
        ) as session_factory:
            await run_email_worker(stop_event)

    async_client.assert_called_once()
    session_factory.assert_not_called()
    http_client.__aenter__.assert_awaited_once()
    http_client.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_processes_batch_and_closes_session():
    stop_event = asyncio.Event()

    http_client = MagicMock()
    http_client.__aenter__ = AsyncMock(return_value=http_client)
    http_client.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    email_service = MagicMock()
    email_service.process_batch = AsyncMock(return_value=["sent"])

    async def stop_after_batch(*, limit):
        stop_event.set()
        return ["sent"]

    email_service.process_batch.side_effect = stop_after_batch

    with (
        patch(
            "app.workers.email.email_worker.AsyncClient",
            return_value=http_client,
        ),
        patch(
            "app.workers.email.email_worker.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.workers.email.email_worker.UnitOfWork",
            return_value=uow,
        ),
        patch(
            "app.workers.email.email_worker.register_notification_repositories"
        ) as register_repositories,
        patch(
            "app.workers.email.email_worker.get_email_delivery_service",
            return_value=email_service,
        ) as get_service,
    ):
        await run_email_worker(stop_event)

    register_repositories.assert_called_once_with(uow)
    get_service.assert_called_once_with(
        uow=uow,
        http_client=http_client,
    )
    email_service.process_batch.assert_awaited_once()
    session.__aenter__.assert_awaited_once()
    session.__aexit__.assert_awaited_once()
    uow.__aenter__.assert_awaited_once()
    uow.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_continues_after_polling_cycle_failure():
    stop_event = asyncio.Event()

    http_client = MagicMock()
    http_client.__aenter__ = AsyncMock(return_value=http_client)
    http_client.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    email_service = MagicMock()

    async def process_batch(*, limit):
        if email_service.process_batch.await_count == 1:
            raise RuntimeError("Temporary database failure")

        stop_event.set()
        return []

    email_service.process_batch = AsyncMock(side_effect=process_batch)

    with (
        patch(
            "app.workers.email.email_worker.AsyncClient",
            return_value=http_client,
        ),
        patch(
            "app.workers.email.email_worker.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.workers.email.email_worker.UnitOfWork",
            return_value=uow,
        ),
        patch("app.workers.email.email_worker.register_notification_repositories"),
        patch(
            "app.workers.email.email_worker.get_email_delivery_service",
            return_value=email_service,
        ),
        patch(
            "app.workers.email.email_worker.settings.EMAIL_WORKER_POLL_INTERVAL_SECONDS",
            0.001,
        ),
    ):
        await run_email_worker(stop_event)

    assert email_service.process_batch.await_count == 2
    assert session.__aenter__.await_count == 2
    assert session.__aexit__.await_count == 2
    assert uow.__aenter__.await_count == 2
    assert uow.__aexit__.await_count == 2


@pytest.mark.asyncio
async def test_worker_closes_resources_when_cancelled():
    stop_event = asyncio.Event()

    http_client = MagicMock()
    http_client.__aenter__ = AsyncMock(return_value=http_client)
    http_client.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    email_service = MagicMock()
    started = asyncio.Event()

    async def process_batch(*, limit):
        started.set()
        await asyncio.Event().wait()

    email_service.process_batch = AsyncMock(side_effect=process_batch)

    with (
        patch(
            "app.workers.email.email_worker.AsyncClient",
            return_value=http_client,
        ),
        patch(
            "app.workers.email.email_worker.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.workers.email.email_worker.UnitOfWork",
            return_value=uow,
        ),
        patch("app.workers.email.email_worker.register_notification_repositories"),
        patch(
            "app.workers.email.email_worker.get_email_delivery_service",
            return_value=email_service,
        ),
    ):
        worker_task = asyncio.create_task(run_email_worker(stop_event))

        await started.wait()
        worker_task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await worker_task

    http_client.__aexit__.assert_awaited_once()
    session.__aexit__.assert_awaited_once()
    uow.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_stops_after_polling_interval_when_stop_requested():
    stop_event = asyncio.Event()

    http_client = MagicMock()
    http_client.__aenter__ = AsyncMock(return_value=http_client)
    http_client.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    email_service = MagicMock()

    async def process_batch(*, limit):
        stop_event.set()
        return []

    email_service.process_batch = AsyncMock(side_effect=process_batch)

    with (
        patch(
            "app.workers.email.email_worker.AsyncClient",
            return_value=http_client,
        ),
        patch(
            "app.workers.email.email_worker.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.workers.email.email_worker.UnitOfWork",
            return_value=uow,
        ),
        patch("app.workers.email.email_worker.register_notification_repositories"),
        patch(
            "app.workers.email.email_worker.get_email_delivery_service",
            return_value=email_service,
        ),
    ):
        await run_email_worker(stop_event)

    email_service.process_batch.assert_awaited_once()
    session.__aenter__.assert_awaited_once()
    session.__aexit__.assert_awaited_once()
    http_client.__aexit__.assert_awaited_once()
