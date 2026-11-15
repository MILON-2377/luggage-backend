import hashlib
import hmac

from app.core.contracts.security.token_hasher import TokenHasher


class SHA256TokenHasher(TokenHasher):
    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def verify_token(self, token: str, token_hash: str) -> bool:
        calculated_hash = self.hash_token(token)

        return hmac.compare_digest(calculated_hash, token_hash)
