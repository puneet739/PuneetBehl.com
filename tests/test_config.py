from app.config import Settings


def test_dry_run_true_when_mail_dry_run_set_even_with_key():
    s = Settings(secret_key="x", resend_api_key="re_key", mail_dry_run=True)
    assert s.dry_run is True


def test_dry_run_false_when_disabled_and_key_present():
    s = Settings(secret_key="x", resend_api_key="re_key", mail_dry_run=False)
    assert s.dry_run is False


def test_dry_run_true_when_disabled_but_key_missing():
    s = Settings(secret_key="x", resend_api_key="", mail_dry_run=False)
    assert s.dry_run is True


def test_dry_run_defaults_failsafe_with_only_secret_key():
    s = Settings(secret_key="x")
    assert s.dry_run is True
