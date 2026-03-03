from app.readiness import ReadinessController, ReadinessState


def test_readiness_progression_to_ready_requires_probe_then_promotion():
    controller = ReadinessController()

    controller.advance(wan_path_ok=True, allow_promotion=False)
    assert controller.state == ReadinessState.PROBING

    controller.advance(wan_path_ok=True, allow_promotion=True)
    assert controller.state == ReadinessState.READY


def test_readiness_demotes_on_wan_failure():
    controller = ReadinessController()

    controller.advance(wan_path_ok=True, allow_promotion=False)
    controller.advance(wan_path_ok=False, allow_promotion=False)

    assert controller.state == ReadinessState.NOT_READY
