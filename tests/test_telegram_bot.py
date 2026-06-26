import pytest
import yaml
from unittest.mock import patch, MagicMock
from src.notifier.telegram_bot import TelegramNotifier

@pytest.fixture
def temp_tg_config(tmp_path):
    config_data = {
        "notifications": {
            "telegram": {
                "bot_token": "123456:ABC-DEF",
                "chat_id": "@my_channel"
            }
        }
    }
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f)
    return str(cfg_file)

@patch("requests.post")
def test_telegram_notifier_send(mock_post, temp_tg_config):
    # Mock response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp
    
    notifier = TelegramNotifier(config_path=temp_tg_config)
    
    tenders = [
        {
            "link": "https://example.com/t1",
            "title": "İhale 1",
            "summary": "Özet 1",
            "source": "dmo",
            "sector": "Demiryolu"
        }
    ]
    
    success = notifier.send_notification(tenders)
    
    assert success is True
    assert mock_post.call_count == 1
    
    # Gönderilen payload'u incele
    call_args = mock_post.call_args[1]
    payload = call_args["json"]
    
    assert payload["chat_id"] == "@my_channel"
    assert payload["parse_mode"] == "HTML"
    assert "📁 Demiryolu" in payload["text"]
    assert "İhale 1" in payload["text"]
    assert "https://example.com/t1" in payload["text"]

@patch("requests.post")
def test_telegram_notifier_message_splitting(mock_post, temp_tg_config):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp
    
    notifier = TelegramNotifier(config_path=temp_tg_config)
    
    # 4000 karakteri aşacak sayıda büyük ihale ekleyelim
    tenders = []
    for i in range(15):
        tenders.append({
            "link": f"https://example.com/large_{i}",
            "title": f"Çok Uzun Başlıklı İhale Tanımı Adı {i} " * 10,
            "summary": "Detay açıklaması " * 10,
            "source": "dmo",
            "sector": "Su Arıtma"
        })
        
    success = notifier.send_notification(tenders)
    
    assert success is True
    # Bölme nedeniyle en az 2 kere istek atılmış olmalı
    assert mock_post.call_count >= 2
