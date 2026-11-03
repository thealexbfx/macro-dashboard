"""Transport safety regressions; synthetic responses and disposable SQLite only."""

from datetime import timedelta
from email.utils import format_datetime
from unittest.mock import Mock

import pytest
import requests

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.runner import Ingestion
from backend.app.ingestion.world_bank import WorldBank, retry_after_seconds
from backend.app.v2.state import Store
from backend.tests.test_phase4a_ingestion import NOW, Fake, records, workbook


def transport(status=200, headers=None, chunks=None):
    response = Mock(status_code=status, headers=headers or {})
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.iter_content.return_value = chunks if chunks is not None else [workbook()]
    session = Mock()
    session.get.return_value = response
    return WorldBank(session, now_fn=lambda: NOW), session, response


@pytest.mark.parametrize("status", [301, 302, 307, 308, 403, 429, 503])
def test_denial_or_redirect_never_followed_or_retried(status):
    provider, session, response = transport(
        status,
        {
            "Location": "https://unapproved.invalid/secret-token",
            "Set-Cookie": "authorization=synthetic-secret",
            "Server": "cloudflare",
            "cf-mitigated": "challenge",
            "Authorization": "Bearer synthetic-secret",
        },
    )
    with pytest.raises(ProviderError, match=f"http_{status}"):
        provider.fetch()
    assert session.get.call_count == 1
    assert session.get.call_args.kwargs["allow_redirects"] is False
    response.iter_content.assert_not_called()
    assert "synthetic-secret" not in str(provider.download_diagnostics)
    assert "unapproved" not in str(provider.download_diagnostics)
    assert provider.download_diagnostics["challenge"] is True


@pytest.mark.parametrize(
    "value,expected",
    [
        ("900", 900),
        ("999999999999999999999999999", 86400),
        ("-1", 0),
        ("not-a-date", 0),
        ("1" * 129, 0),
        (format_datetime(NOW + timedelta(seconds=601)), 601),
        (format_datetime(NOW - timedelta(seconds=30)), 0),
        (format_datetime(NOW + timedelta(days=8)), 86400),
    ],
)
def test_retry_after_dates_and_bounds(value, expected):
    assert retry_after_seconds(value, NOW) == expected


def test_http_date_reaches_durable_backoff_and_last_good_survives(tmp_path):
    clock = [NOW]
    engine = Ingestion(
        Store(tmp_path / "transport.db"), [Fake()], now_fn=lambda: clock[0]
    )
    engine.run_once(force=True)
    before = records(engine)
    provider, session, response = transport(
        503, {"Retry-After": format_datetime(NOW + timedelta(seconds=900))}
    )
    engine.adapters["world_bank"] = provider
    failed = engine.run_once(force=True)
    assert failed["error_code"] == "http_503"
    with engine.store.connection() as db:
        job = dict(db.execute("SELECT * FROM ingest_jobs").fetchone())
    assert job["next_due"] == NOW.timestamp() + 900
    assert records(engine) == before
    assert engine.run_once()["state"] == "idle"
    assert session.get.call_count == 1
    response.status_code, response.headers = 200, {}
    response.iter_content.return_value = [workbook()]
    clock[0] += timedelta(seconds=901)
    assert engine.run_once()["state"] == "unchanged"
    assert records(engine) == before


@pytest.mark.parametrize(
    "mime", ["text/html; charset=utf-8", "application/json", "text/plain"]
)
def test_200_challenge_or_error_is_rejected_before_read(mime):
    provider, _, response = transport(headers={"Content-Type": mime})
    with pytest.raises(ProviderError, match="unexpected_content_type"):
        provider.fetch()
    response.iter_content.assert_not_called()
    assert provider._cached is None


@pytest.mark.parametrize(
    "mime",
    [
        "",
        "application/octet-stream",
        "application/zip",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ],
)
def test_binary_or_absent_mime_still_requires_valid_workbook(mime):
    provider, session, _ = transport(headers={"Content-Type": mime})
    batch = provider.fetch()
    assert len(batch.points) == 72
    assert provider.fetch() is batch
    assert session.get.call_count == 1
    provider, _, _ = transport(
        headers={"Content-Type": mime}, chunks=[b"<html>denied</html>"]
    )
    with pytest.raises(ProviderError, match="malformed_workbook"):
        provider.fetch()


@pytest.mark.parametrize("length", ["4194305", "999999999999999999999999"])
def test_oversize_declared_body_is_not_read(length):
    provider, _, response = transport(headers={"Content-Length": length})
    with pytest.raises(ProviderError, match="download_too_large"):
        provider.fetch()
    response.iter_content.assert_not_called()


@pytest.mark.parametrize(
    "error,code",
    [
        (requests.exceptions.SSLError("synthetic-secret"), "tls_error"),
        (requests.Timeout("synthetic-secret"), "download_timeout"),
        (requests.ConnectionError("synthetic-secret"), "provider_unavailable"),
    ],
)
def test_transport_error_is_classified_without_exception_text(error, code):
    provider, session, _ = transport()
    session.get.side_effect = error
    with pytest.raises(ProviderError, match=code) as raised:
        provider.fetch()
    assert str(raised.value) == code
    assert "synthetic-secret" not in str(provider.download_diagnostics)


def test_failed_fetch_does_not_serve_expired_batch():
    provider, session, _ = transport()
    provider.fetch()
    provider._expires = 0
    session.get.side_effect = requests.Timeout()
    with pytest.raises(ProviderError, match="download_timeout"):
        provider.fetch()


def test_read_only_probe_outputs_no_values_or_sensitive_headers():
    from scripts.probe_worldbank_access import probe

    provider, _, _ = transport(
        headers={
            "Content-Type": "application/octet-stream",
            "Server": "Bearer synthetic-secret",
        }
    )
    result = probe(provider)
    assert result["ok"] and result["database_access"] is False
    assert result["download"]["edge"] == "unknown"
    assert "value" not in str(result) and "synthetic-secret" not in str(result)
    assert result["series"]["wb_copper_monthly"]["non_missing"] == 24


def test_urllib_denial_does_not_read_body_or_leak_headers():
    import urllib.error

    from scripts.probe_worldbank_access import urllib_probe

    body = Mock()
    error = urllib.error.HTTPError(
        "https://fixed.invalid",
        403,
        "synthetic-secret",
        {"Authorization": "synthetic-secret", "cf-mitigated": "challenge"},
        body,
    )
    opener = Mock()
    opener.open.side_effect = error
    result = urllib_probe(opener)
    assert result["http_status"] == 403 and result["challenge"]
    body.read.assert_not_called()
    assert opener.open.call_count == 1 and "synthetic-secret" not in str(result)


def test_urllib_redirect_handler_never_follows_any_location():
    from scripts.probe_worldbank_access import NoRedirect

    assert (
        NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid")
        is None
    )
