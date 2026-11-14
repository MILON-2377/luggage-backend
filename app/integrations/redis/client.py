from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings
from app.integrations.redis.scripts.loader import RedisScriptLoader


class RedisManager:
    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None
        self._script_loader: RedisScriptLoader | None = None

    async def connect(self) -> None:
        if self._client is not None:
            return

        pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
            health_check_interval=30,
        )
        client = Redis(connection_pool=pool)
        script_loader = RedisScriptLoader(client)

        try:
            await client.ping()
            await script_loader.register(
                name="token_bucket",
                filename="token_bucket.lua",
            )
        except Exception:
            script_loader.clear()
            await client.aclose()
            await pool.aclose()
            raise

        self._pool = pool
        self._client = client
        self._script_loader = script_loader

    async def disconnect(self) -> None:
        if self._script_loader is not None:
            self._script_loader.clear()
            self._script_loader = None

        if self._client is not None:
            await self._client.aclose()
            self._client = None

        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None

    async def is_healthy(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception:
            return False

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis connection has not been initialized.")

        return self._client

    @property
    def scripts(self) -> RedisScriptLoader:
        if self._script_loader is None:
            raise RuntimeError("Redis scripts have not been initialized.")

        return self._script_loader


redis_manager = RedisManager()