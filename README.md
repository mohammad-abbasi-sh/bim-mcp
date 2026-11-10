# bim-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/bim-mcp

Unofficial **read-only** MCP server for bim.com.tr, BİM Birleşik Mağazalar A.Ş. — Turkey's largest hard-discount grocery chain (13,032 stores in Türkiye as of 30.06.2026). Weekly Aktüel deals with prices, product search, price statistics, the 11 product-range categories, and the 81 provinces in the store finder.

> Built by Mohammad Abbasi as part of the "Turkey MCP factory" (Sepehr-style pipeline). Not affiliated with bim.com.tr or BİM.

## For AI agents

Add to your MCP client config (stdio):

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

Or run locally: `python -m bim_mcp.server` (needs `mcp<2`, `curl-cffi`).

## Tools

| Tool | Description |
|------|-------------|
| `bim_list_aktuel_dates` | Aktüel + İndirim date periods — date key, Turkish label (e.g. "03 Kasım Salı"), kind ("aktuel"/"indirim") |
| `bim_aktuel_products` | Priced Aktüel products for one week — `date_key` (omit for current week); `query` Turkish substring filter (e.g. "yağ", "pirinç"); `sort` ("price_asc"/"price_desc"/"name"); `limit` 1..100; brand, name, size, price_try (TL), image_url, product URL, slug, BİM id |
| `bim_product_detail` | Full detail of one product — `slug` from a product URL (e.g. "aycicek-yagi-pet-sise-26-10"); name, size, current price_try (TL), large image_url, BİM id (no brand on the detail page — brand comes from the listing) |
| `bim_price_stats` | Price statistics for one week — count, min/median/mean/max in TL, 5 cheapest and 5 priciest products |
| `bim_list_categories` | The 11 product-range categories (Süt ve Süt Ürünleri, İçecekler, ...) with id, name, slug, URL |
| `bim_list_cities` | The 81 Turkish provinces in BİM's store finder (id + name). Per-city store addresses are NOT available — the finder lookup is session-gated on the site |

Example output (`bim_aktuel_products` / 03 Kasım 2026 week):

```json
{"brand": "TURNA", "name": "AYÇİÇEK YAĞI PET ŞİŞE", "size": "5 L",
 "price_try": 429.0,
 "image_url": "https://cdn1.bim.com.tr/uploads/aktuel-urunler/1697_kucuk_543X467_2080_gda_0051_vector-smart-object.jpg",
 "url": "https://www.bim.com.tr/aktuel-urunler/aycicek-yagi-pet-sise-26-10/aktuel.aspx",
 "slug": "aycicek-yagi-pet-sise-26-10", "bim_id": "72460"}
```

## How it works

bim.com.tr serves its Aktüel pages fully server-rendered — no login, no API key, no session cookies. The Aktüel/İndirim date menu is a table inside `<div class="subMenu aktuelsubmenu">` (rows link `?top=1&Bim_AktuelTarihKey=<key>`). Products are `<div class="product ...">` cards: brand in `<h2 class="subTitle">`, name in `<h2 class="title">`, size in `<div class="gramajadet">`, price split across `<div class="text quantify">429,</div>` + `<span class="number">00</span>` + `<span class="curr">₺</span>` (Turkish formatting: "." thousands, "," decimals). Two of the ~95 blocks per week are image-only banners with no price and are skipped. Categories come from `/Markalar/<id>/<slug>.aspx` links on the product-range page; provinces from the store-finder city dropdown. One site feature is documented, not worked around: the store finder posts to a KuramPortal gate with live page session tokens (bearer + page_SessionToken), so per-city store addresses are not offered. Transport uses Chrome TLS impersonation (`curl-cffi`, `chrome120` with rotation); requests are spaced ~0.8s apart; everything is read-only.

## Install

```bash
uvx bim-mcp==0.1.0        # run directly (needs uv)
# or
pip install bim-mcp==0.1.0
bim-mcp    # starts the MCP server on stdio
```

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Offline tests run on recorded fixtures (real pages fetched 2026-11-10); live tests hit bim.com.tr. Tests green at build time (see repo for counts) plus an MCP stdio smoke test.

## Roadmap

- Aktüel poster (Afişler) pages — weekly brochure images per date key
- Store lookup if BİM ever publishes a session-free endpoint
- Price history across Aktüel weeks (compare the same product week to week)

## License

MIT — see [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
