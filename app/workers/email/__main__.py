import asyncio

from app.cli.email.email_worker import main

if __name__ == "__main__":
    asyncio.run(main())
