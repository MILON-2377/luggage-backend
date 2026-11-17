import uuid

from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.generators.uuid_generator import UUIDGenerator


def test_uuid_generator_implements_contract() -> None:
    generator = UUIDGenerator()

    assert isinstance(generator, AbstractIDGenerator)
    assert isinstance(generator.generate(), uuid.UUID)
