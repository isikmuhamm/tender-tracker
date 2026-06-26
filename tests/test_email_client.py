import pytest
import yaml
from unittest.mock import MagicMock, patch
from src.notifier.email_client import EmailNotifier

@pytest.fixture
def temp_config_file(tmp_path):
    config_data = {
        "notifications": {
            "email": {
                "smtp_server": "smtp.test.com",
                "smtp_port": 587,
                "sender": "sender@test.com",
                "password": "testpass",
                "recipients": ["rcpt1@test.com", "rcpt2@test.com"]
            }
        }
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f)
    return str(cfg_file)

@patch("smtplib.SMTP")
def test_email_notifier_send(mock_smtp_class, temp_config_file):
    # SMTP mock nesnelerini ayarla
    mock_smtp = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp
    
    notifier = EmailNotifier(config_path=temp_config_file)
    
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

def test_email_notifier_empty_tenders(temp_config_file):
    notifier = EmailNotifier(config_path=temp_config_file)
    # Boş ihale listesi gönderildiğinde SMTP çağrılmadan doğrudan True dönmeli
    with patch("smtplib.SMTP") as mock_smtp_class:
        success = notifier.send_notification([])
        assert success is True
        mock_smtp_class.assert_not_called()
