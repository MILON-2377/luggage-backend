from app.integrations.security.argon2_password_hasher import Argon2PasswordHasher


def test_hash_password() -> None:
    hasher = Argon2PasswordHasher()

    hashed = hasher.hash_password("StrongPassword123!")

    assert hashed != "StrongPassword123!"
    assert hasher.verify_password("StrongPassword123!", hashed)


def test_verify_incorrect_password() -> None:
    hasher = Argon2PasswordHasher()

    hashed = hasher.hash_password("StrongPassword123!")

    assert not hasher.verify_password("WrongPassword123!", hashed)


def test_verify_and_update_password() -> None:
    hasher = Argon2PasswordHasher()

    hashed = hasher.hash_password("StrongPassword123!")

    verified, updated_hash = hasher.verify_and_update_password(
        "StrongPassword123!",
        hashed,
    )

    assert verified is True
    assert updated_hash is None
