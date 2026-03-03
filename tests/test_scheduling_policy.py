from app.readiness import ReadinessState
from app.scheduling_policy import PollSpeed, SchedulingPolicy


def test_next_schedule_uses_fast_poll_for_non_ready_states(monkeypatch):
    monkeypatch.setattr("app.scheduling_policy.random.uniform", lambda a, b: 2.5)

    policy = SchedulingPolicy(
        cycle_interval_s=60,
        polling_jitter_s=10,
        fast_poll_scalar=0.5,
        slow_poll_scalar=2.0,
    )

    decision = policy.next_schedule(elapsed=5, readiness=ReadinessState.PROBING)

    assert decision.poll_speed == PollSpeed.FAST
    assert decision.base_interval == 30
    assert decision.jitter == 2.5
    assert decision.sleep_for == 27.5


def test_next_schedule_clamps_sleep_to_zero(monkeypatch):
    monkeypatch.setattr("app.scheduling_policy.random.uniform", lambda a, b: 0.0)

    policy = SchedulingPolicy(
        cycle_interval_s=10,
        polling_jitter_s=0,
        fast_poll_scalar=0.5,
        slow_poll_scalar=1.0,
    )

    decision = policy.next_schedule(elapsed=20, readiness=ReadinessState.READY)

    assert decision.poll_speed == PollSpeed.SLOW
    assert decision.sleep_for == 0.0
