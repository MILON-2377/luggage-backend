import uuid

from app.core.contracts.generators.id_generator import AbstractIDGenerator


class UUIDGenerator(AbstractIDGenerator):
    def generate(self) -> uuid.UUID:
        return uuid.uuid4()
