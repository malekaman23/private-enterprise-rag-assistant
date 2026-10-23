import json

import config
import auth
import privacy_guard
import integration_actions
import rate_limit
from enterprise.connectors import status as connector_status
from enterprise.data_sources import catalog as data_source_catalog
from vector_store import _access_filter
from tenant_utils import safe_scope


def test_scope_values_are_path_safe():
    assert safe_scope("company/acme..secret", "fallback") == "company_acme..secret"
    assert safe_scope("", "fallback") == "fallback"


def test_authentication_maps_principal(monkeypatch):
    monkeypatch.setattr(config, "API_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(config, "API_TENANT_ID", "company-a")
    monkeypatch.setattr(config, "API_USER_ID", "user-1")
    principal = auth.authenticate("test-token")
    assert principal.tenant_id == "company-a"
    assert principal.user_id == "user-1"
    assert auth.authenticate("wrong-token") is None


def test_sensitive_content_is_detected():
    assert privacy_guard.contains_sensitive_data("my phone number is 9876543210")
    assert privacy_guard.contains_sensitive_data("my PAN card is ABCDE1234F")


def test_cloud_sensitive_terms_are_not_required_for_normal_text():
    assert not privacy_guard.contains_sensitive_data("summarize this project roadmap")


def test_integration_actions_are_approval_gated_and_reject_raw_payment_data(monkeypatch):
    monkeypatch.setattr(integration_actions.action_store, "create_action", lambda *args: 41)
    monkeypatch.setattr(integration_actions.audit_log, "record_event", lambda *args, **kwargs: None)
    result = integration_actions.queue_action(
        "tenant-a", "user-a", "create_payment_link",
        {"amount": "10", "currency": "INR", "description": "invoice"},
    )
    assert "#41" in result
    try:
        integration_actions.queue_action(
            "tenant-a", "user-a", "create_payment_link", {"card_number": "4111"}
        )
    except ValueError as exc:
        assert "Raw card" in str(exc)
    else:
        raise AssertionError("raw payment data must be rejected")


def test_rate_limiter_blocks_after_limit(monkeypatch):
    rate_limit._local_buckets.clear()
    monkeypatch.setattr(rate_limit, "_redis_client", lambda: None)
    assert rate_limit.allow("test-rate-key", limit=2)
    assert rate_limit.allow("test-rate-key", limit=2)
    assert not rate_limit.allow("test-rate-key", limit=2)


def test_department_filter_contains_only_allowed_scopes():
    access = _access_filter("company-a", "user-1", ("sales",))
    serialized = json.dumps(access)
    assert "sales" in serialized
    assert "user-1" in serialized
    assert "finance" not in serialized


def test_external_connectors_are_disabled_by_default(monkeypatch):
    monkeypatch.setattr(config, "WHATSAPP_CONNECTOR_URL", "")
    monkeypatch.setattr(config, "WHATSAPP_CONNECTOR_ENABLED", "false")
    whatsapp = next(item for item in connector_status() if item["name"] == "whatsapp")
    assert whatsapp["configured"] is False
    assert whatsapp["enabled"] is False
    assert whatsapp["requires_approval"] is True


def test_data_source_catalog_is_provider_neutral_and_secret_free():
    sources = data_source_catalog()
    keys = {source["key"] for source in sources}
    assert {"smb_nas", "s3", "sharepoint", "postgresql", "private_api"} <= keys
    assert all("token" not in str(source).lower() for source in sources)
