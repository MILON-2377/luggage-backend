import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cli.email.email_worker import main


@pytest.mark.asyncio
async def test_email_worker_cli_starts_and_runs_worker():
    stop_event_received = None

    async def fake_run_worker(stop_event):
        nonlocal stop_event_received
        stop_event_received = stop_event
        assert isinstance(stop_event, asyncio.Event)

    mock_loop = MagicMock()
    mock_loop.add_signal_handler = MagicMock()

    with (
        patch(
            "app.cli.email.email_worker.asyncio.get_running_loop",
            return_value=mock_loop,
        ),
        patch(
            "app.cli.email.email_worker.run_email_worker",
            new_callable=AsyncMock,
            side_effect=fake_run_worker,
        ) as run_worker,
        patch("app.cli.email.email_worker.logging.basicConfig"),
    ):
        await main()

    run_worker.assert_awaited_once()
    assert isinstance(stop_event_received, asyncio.Event)
    assert mock_loop.add_signal_handler.call_count == 2


@pytest.mark.asyncio
async def test_sigterm_requests_graceful_worker_shutdown():
    handlers = {}

    mock_loop = MagicMock()

    def register_handler(sig, callback):
        handlers[sig] = callback

    mock_loop.add_signal_handler.side_effect = register_handler

    async def fake_run_worker(stop_event):
        assert not stop_event.is_set()
        handlers[signal.SIGTERM]()
        assert stop_event.is_set()

    with (
        patch(
            "app.cli.email.email_worker.asyncio.get_running_loop",
            return_value=mock_loop,
        ),
        patch(
            "app.cli.email.email_worker.run_email_worker",
            new_callable=AsyncMock,
            side_effect=fake_run_worker,
        ) as run_worker,
        patch("app.cli.email.email_worker.logging.basicConfig"),
    ):
        await main()

    run_worker.assert_awaited_once()
    assert signal.SIGINT in handlers
    assert signal.SIGTERM in handlers




@pytest.mark.asyncio
async def test_sigint_requests_graceful_worker_shutdown():
    handlers = {}

    mock_loop = MagicMock()
    mock_loop.add_signal_handler.side_effect = (
        lambda sig, callback: handlers.__setitem__(sig, callback)
    )

    async def fake_run_worker(stop_event):
        handlers[signal.SIGINT]()
        assert stop_event.is_set()

    with (
        patch(
            "app.cli.email.email_worker.asyncio.get_running_loop",
            return_value=mock_loop,
        ),
        patch(
            "app.cli.email.email_worker.run_email_worker",
            new_callable=AsyncMock,
            side_effect=fake_run_worker,
        ) as run_worker,
        patch("app.cli.email.email_worker.logging.basicConfig"),
    ):
        await main()

    run_worker.assert_awaited_once()
    assert signal.SIGINT in handlers
    assert signal.SIGTERM in handlers