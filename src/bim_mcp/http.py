"""HTTP layer for bim_mcp.

bim.com.tr serves its Aktüel (weekly deals) pages fully
server-rendered — product cards with brand, name, size, price and
image, plus the Aktüel/İndirim date menus — with plain HTTP 200,
no login, no API key, no session cookies (verified live
2026-11-10). The site is ASP.NET served as UTF-8. Transport
still uses curl-cffi Chrome impersonation, the proven pattern of
the other Turkey-factory servers. Requests are kept gentle (one
at a time, ~0.8s apart) and read-only. GET only.

VM note: on this VM outbound HTTPS goes through an egress proxy;
the MCP stdio client spawns servers with a minimal environment
(no proxy variables), so client-spawned runs here need the proxy
variables forwarded (see tests/smoke_mcp.py) or requests die
mid-TLS (curl 35, connection reset). On a normal machine with
direct internet this does not apply.

One site feature is documented, not worked around: the store
finder (/Categories/104/magazalar.aspx) is a KuramPortal-gated
workflow that needs live page session tokens (bearer +
page_SessionToken), so store-by-city lookup is NOT offered —
only the 81-province list the page itself publishes.
"""
from __future__ import annotations

import time
from urllib.parse import quote

from curl_cffi import requests as _r

BASE = "https://www.bim.com.tr"
TIMEOUT = 30.0
MIN_INTERVAL = 0.8  # seconds between requests — be polite

_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

_last_fetch = 0.0


class BimError(RuntimeError):
    pass


_PROFILES = ("chrome120", "chrome131", "safari17_0")
_MAX_ATTEMPTS = 2  # one retry with the next profile
_RETRY_BACKOFF = 1.0  # seconds between attempts
_profile_idx = 0  # sticky: profile that last succeeded


def _request(url: str, headers: dict, timeout: float = TIMEOUT):
    """GET with fingerprint rotation.

    Starts at the sticky profile (chrome120 on a fresh process), retries
    once with the next profile on HTTP 403/429 or a transport error, then
    returns the last response (so the caller raises the specific 403/429
    error) or raises a network error if every attempt failed at the
    transport. Added 2026-11-10 (fleet audit fix).
    """
    global _profile_idx
    last_exc: Exception | None = None
    for k in range(_MAX_ATTEMPTS):
        profile = _PROFILES[(_profile_idx + k) % len(_PROFILES)]
        try:
            resp = _r.get(url, impersonate=profile, headers=headers, timeout=timeout)
        except Exception as e:
            last_exc = e
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            raise BimError(f"network error fetching {url}: {e}") from e
        if resp.status_code in (403, 429):
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            return resp
        _profile_idx = (_profile_idx + k) % len(_PROFILES)
        return resp
    raise BimError(f"network error fetching {url}: {last_exc}") from last_exc


def _get(url: str) -> str:
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = _request(url, _HEADERS)
    except BimError:
        raise
    except Exception as e:
        raise BimError(f"network error fetching {url}: {e}") from e
    finally:
        _last_fetch = time.monotonic()
    if resp.status_code == 403:
        raise BimError(
            "bim.com.tr refused the request (HTTP 403, bot wall) — try again later"
        )
    if resp.status_code == 429:
        raise BimError(
            "bim.com.tr rate-limited the request (HTTP 429) — try again later"
        )
    if resp.status_code in (404, 410):
        raise BimError(
            f"page not found (HTTP {resp.status_code}): {url} — check the "
            "date key / product slug"
        )
    if resp.status_code != 200:
        raise BimError(f"unexpected HTTP {resp.status_code} fetching {url}")
    return resp.content.decode("utf-8", errors="replace")


def fetch_home_html() -> str:
    """Homepage (carries the Aktüel/İndirim date menus)."""
    return _get(f"{BASE}/")


def fetch_aktuel_html(date_key: str | None = None) -> str:
    """Aktüel products page: /Categories/100/aktuel-urunler.aspx
    (optionally ?top=1&Bim_AktuelTarihKey=<key> for one date)."""
    url = f"{BASE}/Categories/100/aktuel-urunler.aspx"
    if date_key:
        url += f"?top=1&Bim_AktuelTarihKey={quote(str(date_key))}"
    return _get(url)


def fetch_product_html(slug: str) -> str:
    """One Aktüel product detail page:
    /aktuel-urunler/<slug>/aktuel.aspx."""
    slug = slug.strip().strip("/")
    if not slug or "/" in slug or ".." in slug:
        raise ValueError("invalid product slug")
    return _get(f"{BASE}/aktuel-urunler/{quote(slug)}/aktuel.aspx")


def fetch_categories_html() -> str:
    """Product-range page: /Categories/102/urun-cesitlerimiz.aspx
    (the 11 Markalar categories)."""
    return _get(f"{BASE}/Categories/102/urun-cesitlerimiz.aspx")


def fetch_stores_html() -> str:
    """Store-finder page: /Categories/104/magazalar.aspx
    (the 81-province dropdown; lookup itself is session-gated)."""
    return _get(f"{BASE}/Categories/104/magazalar.aspx")


def health_check() -> dict:
    """One polite probe of the source site.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `bim_health` tool
    and the daily smoke CI. Added 2026-11-10 (fleet audit fix).
    """
    url = "https://www.bim.com.tr/"
    try:
        fetch_home_html()
    except BimError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
