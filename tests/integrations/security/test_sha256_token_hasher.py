from app.integrations.security.sha256_token_hasher import SHA256TokenHasher


def test_hash_token() -> None:
    hasher = SHA256TokenHasher()

    token_hash = hasher.hash_token("sample-refresh-token")

    assert token_hash != "sample-refresh-token"
    assert len(token_hash) == 64


def test_verify_correct_token() -> None:
    hasher = SHA256TokenHasher()
    token = "sample-refresh-token"

    token_hash = hasher.hash_token(token)

    assert hasher.verify_token(token, token_hash)


def test_reject_incorrect_token() -> None:
    hasher = SHA256TokenHasher()
    token_hash = hasher.hash_token("sample-refresh-token")

    assert not hasher.verify_token("wrong-token", token_hash)
