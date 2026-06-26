import pytest
from unittest.mock import MagicMock, patch
from src.notifier.email_client import EmailNotifier

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("MAIL_FROM", "sender@test.com")
    monkeypatch.setenv("MAIL_PASSWORD", "testpass")
    monkeypatch.setenv("MAIL_TO", "rcpt1@test.com,rcpt2@test.com")

@patch("smtplib.SMTP")
def test_email_notifier_send(mock_smtp_class, mock_env):
    # SMTP mock nesnelerini ayarla
    mock_smtp = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp
    
    notifier = EmailNotifier()
    
    tenders = [
        {
            "link": "https://example.com/t1",
            "title": "Test Demiryolu İhalesi",
            "summary": "Ray yenileme",
            "category": "Yapım",
            "source": "dmo",
            "sector": "Demiryolu"
        },
        {
            "link": "https://example.com/t2",
            "title": "Test Su İhalesi",
            "summary": "Arıtma alımı",
            "category": "Mal Alımı",
            "source": "yatirimlar",
            "sector": "Su Arıtma"
        }
    ]
    
    success = notifier.send_notification(tenders)
    
    assert success is True
    # SMTP metodlarının çağrıldığını doğrula
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("sender@test.com", "testpass")
    mock_smtp.send_message.assert_called_once()
    
    # Gönderilen e-postanın içeriğini kontrol et
    sent_msg = mock_smtp.send_message.call_args[0][0]
    assert sent_msg["From"] == "sender@test.com"
    assert sent_msg["To"] == "rcpt1@test.com, rcpt2@test.com"
    assert "İhale Raporu" in sent_msg["Subject"]

def test_email_notifier_empty_tenders(mock_env):
    notifier = EmailNotifier()
    # Boş ihale listesi gönderildiğinde SMTP çağrılmadan doğrudan True dönmeli
    with patch("smtplib.SMTP") as mock_smtp_class:
        success = notifier.send_notification([])
        assert success is True
        mock_smtp_class.assert_not_called()
