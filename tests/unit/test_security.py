from backend.core.security import PasswordHasher, SecurityError, TokenService


SECRET = "test-secret-key-with-at-least-32-characters"


def test_password_hash_is_salted_and_verifiable() -> None:
    hasher = PasswordHasher()
    first = hasher.hash("correct horse battery staple")
    second = hasher.hash("correct horse battery staple")

    assert first != second
    assert hasher.verify("correct horse battery staple", first)
    assert not hasher.verify("wrong password", first)


def test_signed_access_token_round_trip_and_tamper_detection() -> None:
    service = TokenService(SECRET, lifetime_seconds=60)
    token = service.issue("user-id", "user", "organization-id")

    claims = service.verify(token)

    assert claims.subject == "user-id"
    assert claims.role == "user"
    assert claims.organization_id == "organization-id"

    payload, signature = token.rsplit(".", 1)
    try:
        service.verify(f"{payload}x.{signature}")
    except SecurityError:
        pass
    else:
        raise AssertionError("Tampered token was accepted")
