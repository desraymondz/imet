from backend.config import settings


def test_tests_use_the_test_database():
    assert settings.database_url.endswith("/imet_test")