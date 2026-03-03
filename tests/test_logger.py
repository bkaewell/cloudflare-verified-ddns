from app.logger import get_logger


def test_get_logger_returns_named_logger():
    logger = get_logger("unit-test")
    assert logger.name == "unit-test"
