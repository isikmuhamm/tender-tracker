import pytest
from src.scraper.yatirimlar import YatirimlarScraper

@pytest.fixture
def sample_html():
    return """
    <html>
    <body>
        <div class="news-item">
            <span class="post-category">Demiryolu İhaleleri</span>
            <a href="/haber/tcdd-sinyalizasyon-ihalesi_123456">TCDD Sinyalizasyon Sistemi Modernizasyon İhalesi</a>
            <p>TCDD Genel Müdürlüğü, sinyalizasyon altyapısını yenilemek için ihaleye çıkıyor.</p>
        </div>
        <article class="post-item">
            <span class="post-category">Karayolu İhaleleri</span>
            <a href="https://yatirimlar.com/haber/otoyol-yapim-isi_789101">Ankara-İzmir Otoyolu Yapım İşi İlanı</a>
            <p>Karayolları Genel Müdürlüğü otoyol inşaatı ihalesi açacaktır.</p>
        </article>
        <!-- Geçersiz/Kısa Başlıklı Link -->
        <div>
            <a href="/haber/kisa">Kısa</a>
        </div>
    </body>
    </html>
    """

def test_yatirimlar_parser(sample_html):
    scraper = YatirimlarScraper()
    items = scraper.parse(sample_html)
    
    assert len(items) == 2
    
    # 1. Öge (Göreli URL test)
    assert items[0]["link"] == "https://yatirimlar.com/haber/tcdd-sinyalizasyon-ihalesi_123456"
    assert items[0]["title"] == "TCDD Sinyalizasyon Sistemi Modernizasyon İhalesi"
    assert items[0]["category"] == "Demiryolu İhaleleri"
    assert items[0]["summary"] == "TCDD Genel Müdürlüğü, sinyalizasyon altyapısını yenilemek için ihaleye çıkıyor."
    assert items[0]["source"] == "yatirimlar"
    
    # 2. Öge (Mutlak URL test)
    assert items[1]["link"] == "https://yatirimlar.com/haber/otoyol-yapim-isi_789101"
    assert items[1]["title"] == "Ankara-İzmir Otoyolu Yapım İşi İlanı"
    assert items[1]["category"] == "Karayolu İhaleleri"
    assert items[1]["summary"] == "Karayolları Genel Müdürlüğü otoyol inşaatı ihalesi açacaktır."
    assert items[1]["source"] == "yatirimlar"
