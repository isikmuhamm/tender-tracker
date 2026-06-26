import pytest
from src.scraper.dmo import DmoScraper

@pytest.fixture
def sample_dmo_html():
    return """
    <table>
        <tbody>
            <tr style="cursor:pointer">
                <td class="middle">
                    <a class="btn btn-warning" href="/Ihale/Detay/17691">Detay</a>
                </td>
                <td class="middle">17691</td>
                <td class="middle">BS53JU86VVE</td>
                <td>Yapay Zeka Sunucusu Satın Alınacaktır</td>
                <td>Bilgisayar ve Yan Ürünleri</td>
                <td data-sort="12.06.2026">12.06.2026</td>
                <td data-sort="29.06.2026">29.06.2026</td>
                <td class="center">
                    <b style="color: #ed6033">*** ZEYİLNAME YAYINLANACAKTIR ***</b>
                </td>
            </tr>
            <tr style="cursor:pointer">
                <td class="middle">
                    <a class="btn btn-warning" href="/Ihale/Detay/17700">Detay</a>
                </td>
                <td class="middle">17700</td>
                <td class="middle">XX123YY</td>
                <td>Hastane Mefruşatı Alımı</td>
                <td>Ofis Mobilyaları</td>
                <td data-sort="15.06.2026">15.06.2026</td>
                <td data-sort="30.06.2026">30.06.2026</td>
                <td class="center"></td>
            </tr>
            <!-- Geçersiz satır (kolon sayısı az) -->
            <tr>
                <td>Kısa Satır</td>
            </tr>
        </tbody>
    </table>
    """

def test_dmo_parser(sample_dmo_html):
    scraper = DmoScraper()
    items = scraper.parse(sample_dmo_html)
    
    assert len(items) == 2
    
    # 1. Öge Testi (Zeyilnameli ve açıklamalı)
    assert items[0]["link"] == "https://www.dmo.gov.tr/Ihale/Detay/17691"
    assert items[0]["title"] == "Yapay Zeka Sunucusu Satın Alınacaktır"
    assert items[0]["category"] == "Bilgisayar ve Yan Ürünleri"
    assert items[0]["summary"] == "İhale No: 17691 | Yayın: 12.06.2026 | Bitiş: 29.06.2026 | Durum: *** ZEYİLNAME YAYINLANACAKTIR ***"
    assert items[0]["source"] == "dmo"
    
    # 2. Öge Testi (Durumu boş)
    assert items[1]["link"] == "https://www.dmo.gov.tr/Ihale/Detay/17700"
    assert items[1]["title"] == "Hastane Mefruşatı Alımı"
    assert items[1]["category"] == "Ofis Mobilyaları"
    assert items[1]["summary"] == "İhale No: 17700 | Yayın: 15.06.2026 | Bitiş: 30.06.2026"
    assert items[1]["source"] == "dmo"
