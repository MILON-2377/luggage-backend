from pathlib import Path

from redis.asyncio import Redis
from redis.commands.core import AsyncScript

SCRIPT_DIRECTORY = Path(__file__).parent.resolve()


class RedisScriptLoader:
    def __init__(self, client: Redis) -> None:
        self._client = client
        self._scripts: dict[str, AsyncScript] = {}
        self._filenames: dict[str, str] = {}

    async def register(self, name: str, filename: str) -> AsyncScript:
        existing = self._scripts.get(name)

        if existing is not None:
            if self._filenames[name] != filename:
                raise ValueError(
                    f"Redis script '{name}' is already registered "
                    f"with a different file: {self._filenames[name]}"
                )

            return existing

        script_path = (SCRIPT_DIRECTORY / filename).resolve()

        if SCRIPT_DIRECTORY not in script_path.parents:
            raise ValueError(
                f"Redis Lua script must be inside {SCRIPT_DIRECTORY}: {filename}"
            )

        if not script_path.is_file():
            raise FileNotFoundError(f"Redis Lua script not found: {script_path}")

        script_source = script_path.read_text(encoding="utf-8")

        await self._client.script_load(script_source)

        script = self._client.register_script(script_source)

        self._scripts[name] = script
        self._filenames[name] = filename

        return script

    def get(self, name: str) -> AsyncScript:
        try:
            return self._scripts[name]
        except KeyError as exc:
            raise RuntimeError(
                f"Redis script '{name}' has not been registered."
            ) from exc

    def clear(self) -> None:
        self._scripts.clear()
        self._filenames.clear()