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

def test_local_classification_insufficient_score(temp_sectors_file):
    tc = TenderClassifier(sectors_path=temp_sectors_file)
    tc.ai_enabled = False
    
    # Sadece özette tek bir kelime geçiyor -> puan 1, eşik değer 2'den küçük olduğu için eşleşmez
    sector, method = tc.classify("Genel İhale İlanı", "Bu projede tren kullanılabilir.")
    assert sector is None
    assert method == "none"
