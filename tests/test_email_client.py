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

@patch("smtplib.SMTP")
def test_email_notifier_xss_escaping(mock_smtp_class, temp_config_file):
    mock_smtp = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp
    
    notifier = EmailNotifier(config_path=temp_config_file)
    
    tenders = [
        {
            "link": "javascript:alert(1)",  # Malicious link
            "title": "<b>Danger Title</b> <script>alert(1)</script>",
            "summary": "Malicious summary <img src=x onerror=alert(2)>",
            "category": "<i>Danger Category</i>",
            "source": "dmo",
            "sector": "Demiryolu <iframe src=xxx>"
        }
    ]
    
    success = notifier.send_notification(tenders)
    assert success is True
    
    sent_msg = mock_smtp.send_message.call_args[0][0]
    html_body = sent_msg.get_payload(0).get_payload(decode=True).decode("utf-8")
    
    # Assert html.escape did its job
    assert "&lt;script&gt;" in html_body
    assert "&lt;b&gt;Danger Title&lt;/b&gt;" in html_body
    assert "&lt;img src=x onerror=alert(2)&gt;" in html_body
    assert "&lt;i&gt;Danger Category&lt;/i&gt;" in html_body
    assert "Demiryolu &lt;iframe src=xxx&gt;" in html_body
    
    # Assert URL protocol is safe (link is replaced with #, not javascript:)
    assert 'href="#' in html_body or "href='#" in html_body
    assert "javascript:" not in html_body
