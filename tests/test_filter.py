import pytest
from src.filter import TenderFilter

def test_tender_filter_no_exclude():
    # Boş bir filtreleyici oluşturulursa hiçbir şey elenmemeli
    tf = TenderFilter(config_path="non_existing_config.yaml")
    assert tf.is_excluded("TCDD Tren Hattı Yapımı") is False

def test_tender_filter_with_exclude(tmp_path):
    # Geçici bir config.yaml oluşturup test edelim
    config_file = tmp_path / "config.yaml"
    config_content = """
    global_filters:
      exclude_keywords:
        - "satılık"
        - "kiralık"
    """
    config_file.write_text(config_content, encoding="utf-8")
    
    tf = TenderFilter(config_path=str(config_file))
    
    # Elenmesi gerekenler
    assert tf.is_excluded("Satılık Arsa İlanı") is True
    assert tf.is_excluded("Kiralık Araç Hizmeti Alımı") is True
    assert tf.is_excluded("Bina yapım işi", "kiralık daireler dahildir") is True
    
    # Geçmesi gerekenler
    assert tf.is_excluded("TCDD Demiryolu Sinyalizasyon Yapım İşi") is False
    assert tf.is_excluded("Su Arıtma Tesisi İnşaatı") is False
