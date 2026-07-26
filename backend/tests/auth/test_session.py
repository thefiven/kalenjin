from kalenjin.auth.session import SessionCodec


def test_verify_reverses_create() -> None:
    codec = SessionCodec("secret-key")

    token = codec.create(42)

    assert codec.verify(token) == 42


def test_verify_returns_none_for_a_tampered_token() -> None:
    codec = SessionCodec("secret-key")
    token = codec.create(42)

    assert codec.verify(token + "x") is None


def test_verify_returns_none_for_a_token_signed_with_a_different_key() -> None:
    token = SessionCodec("secret-key-a").create(42)

    assert SessionCodec("secret-key-b").verify(token) is None


def test_verify_returns_none_for_an_expired_token() -> None:
    codec = SessionCodec("secret-key", max_age_seconds=-1)

    token = codec.create(42)

    assert codec.verify(token) is None


def test_verify_returns_none_for_garbage_input() -> None:
    codec = SessionCodec("secret-key")

    assert codec.verify("not-a-real-token") is None
