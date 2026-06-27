import pytest
from src.classifier import TenderClassifier

@pytest.fixture
def temp_sectors_file(tmp_path):
    sectors_file = tmp_path / "sectors.yaml"
    sectors_content = """
    Demiryolu:
      keywords:
        - "tcdd"
        - "demiryolu"
        - "tren"
      negative_keywords:
        - "oyuncak"
    Su Arıtma:
      keywords:
        - "arıtma tesisi"
        - "atıksu"
        - "su arıtma"
      negative_keywords:
        - "damacana"
    """
    sectors_file.write_text(sectors_content, encoding="utf-8")
    return str(sectors_file)

def test_local_classification_success(temp_sectors_file):
    tc = TenderClassifier(sectors_path=temp_sectors_file)
    # AI kapalı modda test ediyoruz
    tc.ai_enabled = False
    
    # Demiryolu eşleşmesi (puan = 2: "tcdd" başlıkta geçti)
    sector, method = tc.classify("TCDD Hat İyileştirme İhalesi")
    assert sector == "Demiryolu"
    assert method == "rule"
    
    # Su Arıtma eşleşmesi (puan = 2: "arıtma tesisi" başlıkta geçti)
    sector, method = tc.classify("Atık Su Arıtma Tesisi Yapımı İlanı")
    assert sector == "Su Arıtma"
    assert method == "rule"
    
    # Açıklamadan eşleşme (başlıkta yok, özette "arıtma tesisi" ve "atıksu" var -> puan 2)
    sector, method = tc.classify("Tesis Yapım İşi", "atıksu arıtma tesisi yapım işidir")
    assert sector == "Su Arıtma"
    assert method == "rule"

def test_local_classification_negative_keywords(temp_sectors_file):
    tc = TenderClassifier(sectors_path=temp_sectors_file)
    tc.ai_enabled = False
    
    # Eşleşen kelime var ("tren") ama negatif kelime de var ("oyuncak") -> elenmeli
    sector, method = tc.classify("TCDD Oyuncak Tren Alımı")
    assert sector is None
    assert method == "none"

def test_local_classification_summary_score(temp_sectors_file):
    tc = TenderClassifier(sectors_path=temp_sectors_file)
    tc.ai_enabled = False
    
    # Sadece özette tek bir kelime geçiyor -> artık eşleşmeli çünkü başlık/özet farkı yok
    sector, method = tc.classify("Genel İhale İlanı", "Bu projede tren kullanılabilir.")
    assert sector == "Demiryolu"
    assert method == "rule"

def test_evaluate_custom_filters_success(temp_sectors_file):
    from unittest.mock import patch
    with patch("src.classifier.LLMClient") as MockLLM:
        mock_instance = MockLLM.return_value
        mock_instance.is_enabled.return_value = True
        mock_instance.complete.return_value = '{"matched_filter_ids": ["filter_1"]}'
        
        tc = TenderClassifier(sectors_path=temp_sectors_file)
        custom_filters = [
            {"id": "filter_1", "name": "Boji Alımı", "prompt_instruction": "Boji veya tekerlek seti alımı içeriyor mu?", "enabled": True},
            {"id": "filter_2", "name": "Yazılım", "prompt_instruction": "Web tabanlı yazılım geliştirme mi?", "enabled": True},
            {"id": "filter_3", "name": "Pasif Filtre", "prompt_instruction": "Devre dışı bırakılmış filtre", "enabled": False}
        ]
        
        matched_ids = tc.evaluate_custom_filters(
            title="Boji ve Tekerlek Seti İhalesi",
            summary="Hızlı trenler için boji alımı yapılacaktır.",
            custom_filters=custom_filters
        )
        
        assert matched_ids == ["filter_1"]
        mock_instance.complete.assert_called_once()
        called_prompt = mock_instance.complete.call_args[0][0]
        assert "Boji ve Tekerlek Seti İhalesi" in called_prompt
        assert "filter_1" in called_prompt
        assert "filter_2" in called_prompt
        assert "filter_3" not in called_prompt

def test_evaluate_custom_filters_invalid_id(temp_sectors_file):
    from unittest.mock import patch
    with patch("src.classifier.LLMClient") as MockLLM:
        mock_instance = MockLLM.return_value
        mock_instance.is_enabled.return_value = True
        mock_instance.complete.return_value = '{"matched_filter_ids": ["invalid_filter_id"]}'
        
        tc = TenderClassifier(sectors_path=temp_sectors_file)
        custom_filters = [
            {"id": "filter_1", "name": "Boji Alımı", "prompt_instruction": "Boji...", "enabled": True}
        ]
        
        matched_ids = tc.evaluate_custom_filters("title", "summary", custom_filters)
        assert matched_ids == []
