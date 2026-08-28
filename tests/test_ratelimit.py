from app.ratelimit import RateLimiter, client_key


def test_allows_up_to_max():
    clock = [1000.0]
    rl = RateLimiter(max_hits=3, window_seconds=60, clock=lambda: clock[0])
    assert [rl.check("a") for _ in range(3)] == [True, True, True]
    assert rl.check("a") is False


def test_separate_keys_independent():
    clock = [1000.0]
    rl = RateLimiter(max_hits=1, window_seconds=60, clock=lambda: clock[0])
    assert rl.check("a") is True
    assert rl.check("b") is True
    assert rl.check("a") is False


def test_window_resets():
    clock = [1000.0]
    rl = RateLimiter(max_hits=1, window_seconds=60, clock=lambda: clock[0])
    assert rl.check("a") is True
    assert rl.check("a") is False
    clock[0] += 61
    assert rl.check("a") is True


def test_client_key_uses_host_and_endpoint():
    class _Req:
        client = type("C", (), {"host": "1.2.3.4"})()

    assert client_key(_Req(), "contact") == "1.2.3.4:contact"


def test_client_key_falls_back_when_no_client():
    class _Req:
        client = None

    assert client_key(_Req(), "contact") == "unknown:contact"
