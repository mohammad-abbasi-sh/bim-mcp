"""MCP server: unofficial read-only access to bim.com.tr (BİM
Birleşik Mağazalar A.Ş. — Turkey's largest hard-discount grocery
chain, 13,032 stores)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import bim as _B
from . import http as _http

mcp = FastMCP("bim-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for bim.com.tr, BİM Birleşik
Mağazalar A.Ş. — Turkey's largest hard-discount grocery chain
(13,032 stores in Türkiye as of 30.06.2026). The weekly Aktüel
deals are the core: every Aktüel/İndirim period has a date key
(Bim_AktuelTarihKey) listed by bim_list_aktuel_dates, and
bim_aktuel_products returns that week's priced products — brand,
Turkish name, size (gramajadet, e.g. "5 L"), price in Turkish
lira, image and detail-page URL. bim_aktuel_products also takes
an optional Turkish query (e.g. "yağ", "pirinç") and a sort
(price_asc / price_desc / name). bim_product_detail re-fetches
one product by its slug (from the product URL) and returns its
current price; the detail page shows no brand — brand comes from
the listing. bim_price_stats gives min/median/mean/max plus the
5 cheapest and 5 priciest products of a week. bim_list_categories
lists the 11 product-range categories (Süt ve Süt Ürünleri,
İçecekler, ...). bim_list_cities lists the 81 provinces in the
store finder; note the store lookup itself is session-gated on
the site (KuramPortal bearer tokens), so this server does not
offer per-city store addresses — only the province list. Data
comes from the site's server-rendered pages — no login, no API
key. Read-only; transport uses Chrome TLS impersonation; requests
are spaced ~0.8s apart. Prices are the Aktüel (promotional)
prices shown on bim.com.tr; verify on the site before acting on
them. Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — Turkey MCP
factory.\
"""


_SOURCE = "bim.com.tr"
_DISCLAIMER = "Unofficial read-only data from bim.com.tr; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


def _validate_limit(limit: int, lo: int = 1, hi: int = 100) -> int:
    if not lo <= limit <= hi:
        raise ValueError(f"limit must be between {lo} and {hi}")
    return limit


@mcp.tool()
def bim_list_aktuel_dates() -> str:
    """Aktüel and İndirim date periods on bim.com.tr, each with its
    date key (Bim_AktuelTarihKey), Turkish label (e.g. "03 Kasım
    Salı", "03-30 Kasım") and kind ("aktuel" or "indirim"). Use a
    key with bim_aktuel_products / bim_price_stats. No arguments."""
    try:
        html_text = _http.fetch_home_html()
        dates = _B.parse_aktuel_dates(html_text)
    except _http.BimError as e:
        return _err(e)
    return _ok({"count": len(dates), "dates": dates})


@mcp.tool()
def bim_aktuel_products(
    date_key: str | None = None,
    query: str | None = None,
    sort: str | None = None,
    limit: int = 50,
) -> str:
    """Priced Aktüel products for one week. date_key: a key from
    bim_list_aktuel_dates; omit for the current week. query:
    optional Turkish substring filter over brand + name + size
    (e.g. "yağ", "pirinç", "süt"). sort: "price_asc",
    "price_desc" or "name" (default: page order). limit 1..100
    (default 50). Returns brand, name, size, price_try (TL),
    image_url, product url, slug and BİM id per product."""
    try:
        _validate_limit(limit)
        if sort is not None and sort not in ("price_asc", "price_desc", "name"):
            raise ValueError('sort must be "price_asc", "price_desc" or "name"')
        html_text = _http.fetch_aktuel_html(date_key)
        products = _B.parse_products(html_text)
        if query:
            products = _B.search_products(products, query)
        if sort == "price_asc":
            products = sorted(products, key=lambda p: p["price_try"])
        elif sort == "price_desc":
            products = sorted(products, key=lambda p: -p["price_try"])
        elif sort == "name":
            products = sorted(products, key=lambda p: p["name"])
    except (ValueError, _http.BimError) as e:
        return _err(e)
    return _ok({
        "date_key": date_key or "current",
        "count": len(products),
        "products": products[:limit],
    })


@mcp.tool()
def bim_product_detail(slug: str) -> str:
    """Full detail of one Aktüel product. slug: the slug from a
    product URL (e.g. "aycicek-yagi-pet-sise-26-10" from
    /aktuel-urunler/aycicek-yagi-pet-sise-26-10/aktuel.aspx).
    Returns name, size, current price_try (TL), large image_url,
    BİM id, slug and url. Note: the detail page shows no brand —
    brand comes from bim_aktuel_products."""
    try:
        if not slug or not str(slug).strip():
            raise ValueError("slug must not be empty")
        html_text = _http.fetch_product_html(str(slug).strip())
        data = _B.parse_product_detail(html_text, str(slug).strip())
    except (ValueError, _http.BimError) as e:
        return _err(e)
    return _ok(data)


@mcp.tool()
def bim_price_stats(date_key: str | None = None) -> str:
    """Price statistics for one Aktüel week: count, min/median/mean/
    max price in TL, the 5 cheapest and 5 priciest products.
    date_key: a key from bim_list_aktuel_dates; omit for the current
    week."""
    try:
        html_text = _http.fetch_aktuel_html(date_key)
        products = _B.parse_products(html_text)
        stats = _B.price_stats(products)
    except (ValueError, _http.BimError) as e:
        return _err(e)
    return _ok({"date_key": date_key or "current", **stats})


@mcp.tool()
def bim_list_categories() -> str:
    """The 11 BİM product-range categories (Süt ve Süt Ürünleri,
    İçecekler, Bakliyat & Unlu Mamüller, ...), each with id, Turkish
    name, slug and URL. No arguments."""
    try:
        html_text = _http.fetch_categories_html()
        cats = _B.parse_categories(html_text)
    except _http.BimError as e:
        return _err(e)
    return _ok({"count": len(cats), "categories": cats})


@mcp.tool()
def bim_list_cities() -> str:
    """The 81 Turkish provinces in BİM's store finder (id + name),
    as published on bim.com.tr. Note: per-city store addresses are
    NOT available — the finder lookup is session-gated on the site.
    No arguments."""
    try:
        html_text = _http.fetch_stores_html()
        cities = _B.parse_cities(html_text)
    except _http.BimError as e:
        return _err(e)
    return _ok({"count": len(cities), "cities": cities})


@mcp.tool()
def bim_health() -> str:
    """Check whether bim.com.tr is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
