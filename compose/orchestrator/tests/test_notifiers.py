from unittest.mock import patch, MagicMock
from app.notifiers import send_telegram, send_email, ping_heartbeat


def test_ping_heartbeat_empty_is_noop():
    assert ping_heartbeat("") is False


@patch("app.notifiers.requests.get")
def test_ping_heartbeat_gets_url(mock_get):
    assert ping_heartbeat("https://hc.example/abc") is True
    assert mock_get.called


@patch("app.notifiers.requests.post")
def test_send_telegram_posts_to_api(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"ok": True})
    ok = send_telegram("tok", "123", "salom")
    assert ok is True
    url = mock_post.call_args[0][0]
    assert "tok/sendMessage" in url


@patch("app.notifiers.smtplib.SMTP")
def test_send_email_uses_smtp(mock_smtp):
    inst = mock_smtp.return_value.__enter__.return_value
    send_email("h", 1025, "f@x", "t@y", "subj", "body")
    assert inst.send_message.called
    assert not inst.starttls.called   # mailhog: TLS yo'q
    assert not inst.login.called      # auth yo'q


def test_send_email_refuses_auth_without_tls():
    import pytest
    with pytest.raises(ValueError):
        send_email("h", 25, "f@x", "t@y", "s", "b", user="u", password="p", use_tls=False)


@patch("app.notifiers.smtplib.SMTP")
def test_send_email_tls_and_login(mock_smtp):
    inst = mock_smtp.return_value.__enter__.return_value
    send_email("smtp.gmail.com", 587, "f@x", "t@y", "s", "b",
               user="u@x", password="pw", use_tls=True)
    assert inst.starttls.called
    inst.login.assert_called_once_with("u@x", "pw")
    assert inst.send_message.called
