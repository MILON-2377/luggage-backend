import asyncio
import logging
import signal

from app.core.config import settings
from app.workers.email.email_worker import run_email_worker


async def main() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await run_email_worker(stop_event)


if __name__ == "__main__":
    asyncio.run(main())
