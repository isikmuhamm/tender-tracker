import pytest
import os
import yaml
from unittest.mock import patch, MagicMock
from run import get_check_interval, show_stats, main

def test_get_check_interval(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    
    with patch("run.get_data_path", return_value=str(config_file)):
        # 1. Default fallback when no config and no env exists
        if config_file.exists():
            config_file.unlink()
        monkeypatch.delenv("CHECK_INTERVAL_MINUTES", raising=False)
        assert get_check_interval() == 60
        
        # 2. Legacy config key fallback
        config_data = {
            "settings": {
                "check_interval": 30
            }
        }
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f)
        assert get_check_interval() == 30
        
        # 3. Canonical config key priority over legacy config key
        config_data_canonical = {
            "settings": {
                "check_interval_minutes": 15,
                "check_interval": 30
            }
        }
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data_canonical, f)
        assert get_check_interval() == 15
        
        # 4. ENV variable priority over config (ENV > config precedence)
        monkeypatch.setenv("CHECK_INTERVAL_MINUTES", "45")
        assert get_check_interval() == 45

@patch("run.SessionLocal")
@patch("run.init_db")
def test_show_stats(mock_init, mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    mock_session.query.return_value.count.return_value = 5
    mock_session.query.return_value.filter_by.return_value.count.return_value = 2
    mock_session.query.return_value.distinct.return_value.all.return_value = [("Demiryolu",), ("İnşaat",)]
    
    show_stats()
    mock_session.close.assert_called_once()

@patch("run.TenderBotOrchestrator")
@patch("run.parse_arguments")
def test_main_once(mock_parse, mock_orch_class):
    mock_args = MagicMock()
    mock_args.once = True
    mock_args.stats = False
    mock_args.daemon = False
    mock_parse.return_value = mock_args
    
    mock_orch = MagicMock()
    mock_orch.run_once.return_value = {"status": "success"}
    mock_orch_class.return_value = mock_orch
    
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    mock_orch.run_once.assert_called_once()

@patch("run.show_stats")
@patch("run.parse_arguments")
def test_main_stats(mock_parse, mock_show_stats):
    mock_args = MagicMock()
    mock_args.once = False
    mock_args.stats = True
    mock_args.daemon = False
    mock_parse.return_value = mock_args
    
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    mock_show_stats.assert_called_once()

@patch("run.time.sleep", side_effect=KeyboardInterrupt)
@patch("run.TenderBotOrchestrator")
@patch("run.parse_arguments")
def test_main_daemon(mock_parse, mock_orch_class, mock_sleep):
    mock_args = MagicMock()
    mock_args.once = False
    mock_args.stats = False
    mock_args.daemon = True
    mock_parse.return_value = mock_args
    
    mock_orch = MagicMock()
    mock_orch_class.return_value = mock_orch
    
    with pytest.raises(SystemExit):
        main()
        
    mock_orch.run_once.assert_called_once()
