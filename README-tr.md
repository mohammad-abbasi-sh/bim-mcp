# bim-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/bim-mcp

bim.com.tr (BİM Birleşik Mağazalar A.Ş. — Türkiye'nin en büyük indirim market zinciri, 30.06.2026 itibarıyla Türkiye'de 13.032 mağaza) için resmi olmayan **salt okunur** MCP sunucusu. Haftalık Aktüel ürünleri fiyatlarıyla, ürün arama, fiyat istatistikleri, 11 ürün kategorisi ve mağaza bulucudaki 81 il.

> Mohammad Abbasi tarafından "Turkey MCP factory" (Sepehr tarzı hat) kapsamında geliştirildi. bim.com.tr veya BİM ile bağlantısı yoktur.

## Yapay zekâ ajanları için

MCP istemci yapılandırmanıza ekleyin (stdio):

```json
{
  "mcpServers": {
    "bim": {
      "command": "uvx",
      "args": ["bim-mcp==0.1.0"]
    }
  }
}
```

Veya yerelde çalıştırın: `python -m bim_mcp.server` (`mcp<2`, `curl-cffi` gerekir).

## Araçlar

| Araç | Açıklama |
|------|-------------|
| `bim_list_aktuel_dates` | Aktüel + İndirim tarih dönemleri — tarih anahtarı, Türkçe etiket (örn. "03 Kasım Salı"), tür ("aktuel"/"indirim") |
| `bim_aktuel_products` | Bir haftanın fiyatlı Aktüel ürünleri — `date_key` (geçerli hafta için boş bırakın); `query` Türkçe alt dize filtresi (örn. "yağ", "pirinç"); `sort` ("price_asc"/"price_desc"/"name"); `limit` 1..100; marka, ad, gramaj, fiyat (TL), görsel, ürün URL'si, slug, BİM kimliği |
| `bim_product_detail` | Bir ürünün tam detayı — ürün URL'sindeki `slug` (örn. "aycicek-yagi-pet-sise-26-10"); ad, gramaj, güncel fiyat (TL), büyük görsel, BİM kimliği (detay sayfasında marka yoktur — marka listeden gelir) |
| `bim_price_stats` | Bir haftanın fiyat istatistikleri — adet, en düşük/ortanca/ortalama/en yüksek fiyat (TL), en ucuz 5 ve en pahalı 5 ürün |
| `bim_list_categories` | 11 ürün kategorisi (Süt ve Süt Ürünleri, İçecekler, ...) — kimlik, ad, slug, URL |
| `bim_list_cities` | BİM mağaza bulucudaki 81 il (kimlik + ad). İl bazında mağaza adresleri YOKTUR — bulucu araması sitede oturum korumalıdır |

Örnek çıktı (`bim_aktuel_products` / 03 Kasım 2026 haftası):

```json
{"brand": "TURNA", "name": "AYÇİÇEK YAĞI PET ŞİŞE", "size": "5 L",
 "price_try": 429.0,
 "image_url": "https://cdn1.bim.com.tr/uploads/aktuel-urunler/1697_kucuk_543X467_2080_gda_0051_vector-smart-object.jpg",
 "url": "https://www.bim.com.tr/aktuel-urunler/aycicek-yagi-pet-sise-26-10/aktuel.aspx",
 "slug": "aycicek-yagi-pet-sise-26-10", "bim_id": "72460"}
```

## Nasıl çalışır?

bim.com.tr, Aktüel sayfalarını tamamen sunucu taraflı sunar — giriş yok, API anahtarı yok, oturum çerezi yok. Aktüel/İndirim tarih menüsü `<div class="subMenu aktuelsubmenu">` içindeki bir tablodur (satırlar `?top=1&Bim_AktuelTarihKey=<anahtar>` bağlantısı verir). Ürünler `<div class="product ...">` kartlarıdır: marka `<h2 class="subTitle">`, ad `<h2 class="title">`, gramaj `<div class="gramajadet">`, fiyat `<div class="text quantify">429,</div>` + `<span class="number">00</span>` + `<span class="curr">₺</span>` biçiminde bölünmüştür (Türkçe biçim: "." binlik, "," ondalık). Haftada ~95 bloktan 2'si fiyatsız, yalnızca görselli afiş kartıdır ve atlanır. Kategoriler ürün çeşitleri sayfasındaki `/Markalar/<kimlik>/<slug>.aspx` bağlantılarından; iller mağaza bulucu şehir listesinden gelir. Bir site özelliği belgelenmiştir, aşılmamıştır: mağaza bulucu, canlı sayfa oturum belirteçleri (bearer + page_SessionToken) gerektiren bir KuramPortal geçidine gönderim yapar; bu nedenle il bazında mağaza adresi sunulmaz. Aktarım Chrome TLS taklidi kullanır (`curl-cffi`, `chrome120` + dönüşümlü); istekler ~0,8 sn aralıklarla yapılır; her şey salt okunurdur.

## Kurulum

```bash
uvx bim-mcp==0.1.0        # doğrudan çalıştır (uv gerekir)
# veya
pip install bim-mcp==0.1.0
bim-mcp    # MCP sunucusunu stdio üzerinde başlatır
```

## Testler

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Çevrimdışı testler kaydedilmiş örnek sayfalarla çalışır (gerçek sayfalar 2026-11-10'da alındı); canlı testler bim.com.tr'ye bağlanır. Derleme anında testler yeşildir (sayılar için repoya bakın) ve bir MCP stdio duman testi de vardır.

## Yol haritası

- Afişler sayfaları — tarih anahtarına göre haftalık broşür görselleri
- BİM oturumsuz bir uç nokta yayınlarsa mağaza araması
- Aktüel haftaları arasında fiyat geçmişi (aynı ürünün haftadan haftaya karşılaştırması)

## Lisans

MIT — bkz. [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
