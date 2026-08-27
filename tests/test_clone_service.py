import conftest  # noqa: F401  (sets env vars + sys.path before anything else imports config)
from unittest.mock import patch, MagicMock

import clone_service


def _fake_response(json_body, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    return resp


def test_validate_bot_token_rejects_malformed_token():
    result = clone_service.validate_bot_token("not-a-real-token")
    assert result["ok"] is False
    assert "error" in result


@patch("clone_service.requests.post")
def test_validate_bot_token_success(mock_post):
    mock_post.return_value = _fake_response({
        "ok": True,
        "result": {"id": 123456, "is_bot": True, "username": "MyCloneBot", "first_name": "MyClone"}
    })
    result = clone_service.validate_bot_token("123456:AAExampleTokenValue")
    assert result["ok"] is True
    assert result["username"] == "MyCloneBot"


@patch("clone_service.requests.post")
def test_validate_bot_token_bad_token(mock_post):
    mock_post.return_value = _fake_response({"ok": False, "description": "Unauthorized"}, status_code=401)
    result = clone_service.validate_bot_token("000000:BadToken")
    assert result["ok"] is False
    assert "Unauthorized" in result["error"]


@patch("clone_service.requests.post")
def test_get_webhook_info_reports_existing_url(mock_post):
    mock_post.return_value = _fake_response({
        "ok": True,
        "result": {"url": "https://someone-elses-service.example.com/hook"}
    })
    result = clone_service.get_webhook_info("123456:token")
    assert result["ok"] is True
    assert result["url"] == "https://someone-elses-service.example.com/hook"


@patch("clone_service.requests.post")
def test_get_webhook_info_empty_when_none_set(mock_post):
    mock_post.return_value = _fake_response({"ok": True, "result": {"url": ""}})
    result = clone_service.get_webhook_info("123456:token")
    assert result["ok"] is True
    assert result["url"] == ""


@patch("clone_service.requests.post")
def test_set_webhook_surfaces_telegram_error(mock_post):
    mock_post.return_value = _fake_response({"ok": False, "description": "Bad webhook: HTTPS url must be provided"})
    result = clone_service.set_webhook("123456:token", "http://not-https.example.com", "secret")
    assert result["ok"] is False
    assert "HTTPS" in result["error"]


@patch("clone_service.requests.post")
def test_set_webhook_success(mock_post):
    mock_post.return_value = _fake_response({"ok": True, "result": True})
    result = clone_service.set_webhook("123456:token", "https://example.com/api/bot?clone_id=1", "secret123")
    assert result["ok"] is True


@patch("clone_service.requests.post")
def test_network_error_does_not_raise(mock_post):
    import requests
    mock_post.side_effect = requests.exceptions.ConnectionError("boom")
    result = clone_service.validate_bot_token("123456:token")
    assert result["ok"] is False
    assert "Network error" in result["error"]
