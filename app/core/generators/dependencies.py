from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.generators.slug_generator import AbstractSlugGenerator
from app.core.generators.slug_generator import SlugGenerator
from app.core.generators.uuid_generator import UUIDGenerator


@lru_cache(maxsize=1)
def get_id_generator() -> AbstractIDGenerator:
    return UUIDGenerator()


@lru_cache(maxsize=1)
def get_slug_generator() -> AbstractSlugGenerator:
    return SlugGenerator()


IDGeneratorDep = Annotated[AbstractIDGenerator, Depends(get_id_generator)]
SlugGeneratorDep = Annotated[AbstractSlugGenerator, Depends(get_slug_generator)]