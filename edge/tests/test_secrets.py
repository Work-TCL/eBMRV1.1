import stat

from runtime.security.secrets import SecretStore


def test_secret_file_written_with_restrictive_permissions(tmp_path):
    store = SecretStore(tmp_path / "secrets")
    store.put("bearer_token", "sid_abc123")

    path = tmp_path / "secrets" / "bearer_token"
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600
    assert store.get("bearer_token") == "sid_abc123"
    assert store.verify_permissions("bearer_token") is True


def test_secret_name_cannot_escape_directory(tmp_path):
    store = SecretStore(tmp_path / "secrets")
    import pytest

    with pytest.raises(ValueError):
        store.put("../escape", "value")


def test_missing_secret_returns_none(tmp_path):
    store = SecretStore(tmp_path / "secrets")
    assert store.get("nonexistent") is None
    assert store.verify_permissions("nonexistent") is False