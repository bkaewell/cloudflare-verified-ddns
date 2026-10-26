from app.cache import Uptime


def test_uptime_string_is_na_until_first_eligible_sample():
    assert str(Uptime()) == "n/a"
