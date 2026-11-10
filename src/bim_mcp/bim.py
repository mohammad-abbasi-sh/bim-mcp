"""Stdlib parsing for bim.com.tr (BİM Birleşik Mağazalar A.Ş.) pages.

Verified live 2026-11-10 against real pages (fixtures in tests/):
- Aktüel page (/Categories/100/aktuel-urunler.aspx, ~200KB):
  the Aktüel/İndirim date menu is a table inside
  <div class="subMenu aktuelsubmenu"> — two columns
  (AKTÜEL ÜRÜNLER / İNDİRİM), rows of <td class="link"><a
  href="...Bim_AktuelTarihKey=<key>">03 Kasım Salı</a></td>;
  products are <div class="product col-xl-3 ..."> blocks (95 on
  2026-11-10, of which 2 are image-only "justImage" banners with
  no price). Each priced block carries: brand in
  <h2 class="subTitle">, name in <h2 class="title">, size in
  <div class="gramajadet">• 5 L</div>, price split across
  <div class="text quantify">429,</div> +
  <span class="number">00</span> + <span class="curr">₺</span>,
  image in <img src="https://cdn1.bim.com.tr/uploads/
  aktuel-urunler/<key>_kucuk_...">, detail link
  /aktuel-urunler/<slug>/aktuel.aspx and BİM id in data-id="72460".
  Prices use Turkish formatting: thousands "." and the lira part
  before the comma (e.g. "1.299," + "00" = 1299.00 TL).
- Product detail (/aktuel-urunler/<slug>/aktuel.aspx, ~90KB):
  same title/price markup in the rightSide area; the page also
  lists other products below, so detail parsing takes the FIRST
  occurrence of each field (the main product). The detail page
  shows no brand — brand comes from the listing. Size is in the
  first gramajadet ("• 5 L"); the big image is the _buyuk_ variant.
- Product range (/Categories/102/urun-cesitlerimiz.aspx):
  11 categories as /Markalar/<id>/<slug>.aspx links (anchor text
  is the Turkish category name, "&nbsp;"-prefixed); the page
  repeats each link twice — deduped by id.
- Store finder (/Categories/104/magazalar.aspx): the city
  dropdown (name BimFiltre$DrpCity) lists 81 provinces as
  <option value="<id>">Name</option> (value 0 = "Seçiniz").
  The lookup itself posts to a KuramPortal gate with live page
  session tokens, so it is NOT parsed — only the province list.
"""
from __future__ import annotations

import html as _html
import re

BASE = "https://www.bim.com.tr"

_WS = re.compile(r"\s+")
_TR_FOLD = str.maketrans({"İ": "i", "I": "ı"})


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return _WS.sub(" ", _html.unescape(text)).strip()


def _fold(text: str) -> str:
    """Turkish-insensitive lowercase for search matching."""
    return text.translate(_TR_FOLD).casefold()


def _parse_price(whole: str, cents: str) -> float | None:
    """quantify "1.299," + number "00" -> 1299.0."""
    whole = whole.strip().rstrip(",").replace(".", "").replace(" ", "")
    cents = cents.strip()
    if not whole.isdigit() or not cents.isdigit():
        return None
    try:
        return float(f"{int(whole)}.{int(cents):02d}")
    except ValueError:
        return None


def parse_aktuel_dates(page_html: str) -> list[dict]:
    """Aktüel + İndirim date periods from the submenu table.

    Returns [{"key": "1697", "label": "03 Kasım Salı",
    "kind": "aktuel"|"indirim", "url": ...}], in page order,
    deduped by key. Empty İndirim cells (href="") are skipped.
    """
    menu = re.search(
        r'class="subMenu aktuelsubmenu".*?</table>', page_html, re.S
    )
    segment = menu.group(0) if menu else page_html
    dates: list[dict] = []
    seen: set[str] = set()
    rows = re.findall(r"<tr>(.*?)</tr>", segment, re.S)
    for row in rows:
        cells = re.findall(
            r'<td class="link"><a href="([^"]*)">([^<]*)</a></td>', row
        )
        for i, (href, label) in enumerate(cells):
            key_m = re.search(r"Bim_AktuelTarihKey=(\d+)", href)
            if not key_m or not _clean(label):
                continue
            key = key_m.group(1)
            if key in seen:
                continue
            seen.add(key)
            dates.append({
                "key": key,
                "label": _clean(label),
                "kind": "aktuel" if i == 0 else "indirim",
                "url": BASE + href if href.startswith("/") else href,
            })
    return dates


def parse_products(page_html: str) -> list[dict]:
    """Aktüel product cards from an Aktüel page.

    Returns one dict per priced product: brand, name, size (may be
    ""), price_try (float), image_url, url, slug, bim_id.
    Image-only "justImage" banner blocks (no price) are skipped.
    """
    products: list[dict] = []
    parts = re.split(r'<div class="product ', page_html)[1:]
    for part in parts:
        if part.startswith("justImage"):
            continue
        whole_m = re.search(
            r'class="text quantify">([^<]*)</div>', part
        )
        cents_m = re.search(
            r'class="number">([^<]*)</span>', part
        )
        name_m = re.search(r'<h2 class="title">\s*([^<]+?)\s*</h2>', part)
        if not name_m or not whole_m or not cents_m:
            continue
        price = _parse_price(whole_m.group(1), cents_m.group(1))
        if price is None:
            continue
        brand_m = re.search(
            r'<h2 class="subTitle">\s*([^<]*?)\s*</h2>', part
        )
        size_m = re.search(
            r'class="gramajadet">\s*•?\s*([^<]*?)\s*</div>', part
        )
        img_m = re.search(r'<img src="([^"]+)"', part)
        url_m = re.search(r'<a href="(/aktuel-urunler/[^"]+)"', part)
        id_m = re.search(r'data-id="(\d+)"', part)
        slug = ""
        url = ""
        if url_m:
            url = BASE + url_m.group(1)
            slug_m = re.search(r"/aktuel-urunler/([^/]+)/aktuel\.aspx", url)
            slug = slug_m.group(1) if slug_m else ""
        products.append({
            "brand": _clean(brand_m.group(1)) if brand_m else "",
            "name": _clean(name_m.group(1)),
            "size": _clean(size_m.group(1)) if size_m else "",
            "price_try": price,
            "image_url": img_m.group(1) if img_m else "",
            "url": url,
            "slug": slug,
            "bim_id": id_m.group(1) if id_m else "",
        })
    return products


def parse_product_detail(page_html: str, slug: str) -> dict:
    """Main product of a detail page (first occurrence of each
    field — the page lists other products below the main one).

    Returns name, size, price_try, image_url (the _buyuk_ variant),
    bim_id. Brand is not shown on the detail page (see module doc).
    """
    name_m = re.search(r'<h2 class="title">\s*([^<]+?)\s*</h2>', page_html)
    whole_m = re.search(r'class="text quantify">([^<]*)</div>', page_html)
    cents_m = re.search(r'class="number">([^<]*)</span>', page_html)
    size_m = re.search(r'class="gramajadet">\s*•?\s*([^<]*?)\s*</div>', page_html)
    img_m = re.search(r'src="([^"]*_buyuk_[^"]*)"', page_html)
    id_m = re.search(r'data-id="(\d+)"', page_html)
    if not name_m or not whole_m or not cents_m:
        raise ValueError("product detail page has no title/price — check the slug")
    price = _parse_price(whole_m.group(1), cents_m.group(1))
    if price is None:
        raise ValueError("product detail page has an unparsable price")
    return {
        "name": _clean(name_m.group(1)),
        "size": _clean(size_m.group(1)) if size_m else "",
        "price_try": price,
        "image_url": img_m.group(1) if img_m else "",
        "bim_id": id_m.group(1) if id_m else "",
        "slug": slug,
        "url": f"{BASE}/aktuel-urunler/{slug}/aktuel.aspx",
    }


def parse_categories(page_html: str) -> list[dict]:
    """The 11 product-range categories (/Markalar/<id>/<slug>.aspx)."""
    cats: list[dict] = []
    seen: set[str] = set()
    for cid, slug, name in re.findall(
        r'<a[^>]*href="/Markalar/(\d+)/([^"]+)\.aspx"[^>]*>(.*?)</a>',
        page_html, re.S,
    ):
        if cid in seen:
            continue
        seen.add(cid)
        clean = _clean(re.sub(r"<[^>]+>", "", name)).replace("\xa0", " ").strip()
        cats.append({
            "id": cid,
            "name": clean,
            "slug": slug,
            "url": f"{BASE}/Markalar/{cid}/{slug}.aspx",
        })
    return sorted(cats, key=lambda c: int(c["id"]))


def parse_cities(page_html: str) -> list[dict]:
    """The 81 provinces from the store-finder city dropdown."""
    sel = re.search(
        r'<select[^>]*drpCITY[^>]*>(.*?)</select>', page_html, re.S
    )
    if not sel:
        return []
    cities: list[dict] = []
    for value, name in re.findall(
        r'<option value="(\d+)">([^<]*)</option>', sel.group(1)
    ):
        if value == "0":
            continue
        cities.append({"id": value, "name": _clean(name)})
    return cities


def search_products(products: list[dict], query: str) -> list[dict]:
    """Turkish-insensitive substring match over brand + name + size."""
    q = _fold(query.strip())
    if not q:
        return products
    return [
        p for p in products
        if q in _fold(f"{p.get('brand', '')} {p.get('name', '')} {p.get('size', '')}")
    ]


def price_stats(products: list[dict]) -> dict:
    """min / median / mean / max over priced products."""
    prices = sorted(p["price_try"] for p in products if p.get("price_try") is not None)
    if not prices:
        raise ValueError("no priced products in this Aktüel list")
    n = len(prices)
    median = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
    by_price = sorted(products, key=lambda p: p["price_try"])
    return {
        "count": n,
        "min_try": prices[0],
        "median_try": round(median, 2),
        "mean_try": round(sum(prices) / n, 2),
        "max_try": prices[-1],
        "cheapest": by_price[:5],
        "priciest": by_price[-5:][::-1],
    }
