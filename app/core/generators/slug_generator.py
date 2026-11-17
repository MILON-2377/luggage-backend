import re
import secrets
import string
import unicodedata

from app.core.contracts.generators.slug_generator import AbstractSlugGenerator

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_ALPHABET = string.ascii_lowercase + string.digits


class SlugGenerator(AbstractSlugGenerator):
    def __init__(self, max_length: int = 150, fallback: str = "item") -> None:
        self._max_length = max_length
        self._fallback = fallback

    def generate(self, value: str, *, random_suffix_length: int = 0) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        normalized = normalized.encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower()

        slug = _NON_ALNUM_RE.sub("-", normalized).strip("-")

        suffix = ""
        if random_suffix_length > 0:
            suffix = "-" + "".join(
                secrets.choice(_ALPHABET) for _ in range(random_suffix_length)
            )

        slug = slug[: self._max_length - len(suffix)].rstrip("-") or self._fallback

        return slug + suffix
