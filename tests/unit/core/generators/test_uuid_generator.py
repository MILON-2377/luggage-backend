import uuid

from app.core.generators.uuid_generator import UUIDGenerator


def test_generate_returns_uuid() -> None:
    generator = UUIDGenerator()

    result = generator.generate()

    assert isinstance(result, uuid.UUID)


def test_generate_returns_unique_uuids() -> None:
    generator = UUIDGenerator()

    first = generator.generate()
    second = generator.generate()

    assert first != second


def test_generate_returns_version_four_uuid() -> None:
    generator = UUIDGenerator()

    result = generator.generate()

    assert result.version == 4
