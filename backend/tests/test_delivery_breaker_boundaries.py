from app.delivery.breaker import CLOSED, HALF_OPEN, OPEN, CircuitBreaker


def test_success_resets_the_consecutive_failure_count():
    breaker = CircuitBreaker(failure_threshold=2)

    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()

    assert breaker.state == CLOSED
    assert breaker.allow_request() is True

    breaker.record_failure()

    assert breaker.state == OPEN
    assert breaker.allow_request() is False


def test_failed_probe_restarts_the_full_cooldown_at_the_boundary():
    now = 0.0

    def clock():
        return now

    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=30, clock=clock)
    breaker.record_failure()

    now = 29.0
    assert breaker.allow_request() is False

    now = 30.0
    assert breaker.allow_request() is True
    assert breaker.state == HALF_OPEN
    breaker.record_failure()

    now = 59.0
    assert breaker.allow_request() is False

    now = 60.0
    assert breaker.allow_request() is True
    assert breaker.state == HALF_OPEN
