"""Live tests for bim_mcp — real requests to bim.com.tr.

Requires network (plain HTTP 200; transport uses curl-cffi Chrome
impersonation). The server is polite by design (~0.8s between
requests), so this file takes ~15s. Run:
    python -m unittest discover -s tests -v

Aktüel weeks rotate, so tests assert structure and sane ranges,
not exact product lists — except the pinned product detail
(aycicek-yagi-pet-sise-26-10, 429.00 TL on 2026-11-10), which is
history for its week; the detail test only asserts the page still
parses to a priced product when the slug exists, and skips
gracefully if BİM rotated that week's products away.
"""
import json
import unittest

from bim_mcp import bim as B
from bim_mcp import http as H

# Pinned product from the 03 Kasım 2026 Aktüel week.
SLUG = "aycicek-yagi-pet-sise-26-10"


class TestLiveDates(unittest.TestCase):
    def test_dates(self):
        dates = B.parse_aktuel_dates(H.fetch_home_html())
        self.assertGreaterEqual(len(dates), 5)
        kinds = {d["kind"] for d in dates}
        self.assertIn("aktuel", kinds)
        for d in dates:
            self.assertTrue(d["key"].isdigit())
            self.assertTrue(d["label"])
            self.assertTrue(d["url"].startswith("https://www.bim.com.tr/"))


class TestLiveProducts(unittest.TestCase):
    def test_current_week(self):
        products = B.parse_products(H.fetch_aktuel_html())
        self.assertGreater(len(products), 20)
        for p in products:
            self.assertTrue(p["name"])
            self.assertGreater(p["price_try"], 0)
            self.assertLess(p["price_try"], 100000)

    def test_dated_week(self):
        dates = B.parse_aktuel_dates(H.fetch_home_html())
        key = dates[0]["key"]
        products = B.parse_products(H.fetch_aktuel_html(key))
        self.assertGreater(len(products), 20)

    def test_search_and_stats(self):
        products = B.parse_products(H.fetch_aktuel_html())
        rows = B.search_products(products, "süt")
        self.assertGreater(len(rows), 0)
        stats = B.price_stats(products)
        self.assertGreater(stats["count"], 20)
        self.assertLessEqual(stats["min_try"], stats["median_try"])
        self.assertLessEqual(stats["median_try"], stats["max_try"])


class TestLiveDetail(unittest.TestCase):
    def test_pinned_product(self):
        try:
            data = B.parse_product_detail(H.fetch_product_html(SLUG), SLUG)
        except H.BimError as e:
            if "404" in str(e):
                self.skipTest("pinned product rotated off the site")
            raise
        self.assertEqual(data["name"], "AYÇİÇEK YAĞI PET ŞİŞE")
        self.assertEqual(data["price_try"], 429.0)
        self.assertEqual(data["size"], "5 L")


class TestLiveCategoriesCities(unittest.TestCase):
    def test_categories(self):
        cats = B.parse_categories(H.fetch_categories_html())
        self.assertEqual(len(cats), 11)

    def test_cities(self):
        cities = B.parse_cities(H.fetch_stores_html())
        self.assertEqual(len(cities), 81)


class TestLiveServerTools(unittest.TestCase):
    def test_dates_tool_json(self):
        from bim_mcp import server as S

        out = json.loads(S.bim_list_aktuel_dates())
        self.assertIn("dates", out)
        self.assertGreaterEqual(out["count"], 5)
        self.assertEqual(out["source"], "bim.com.tr")

    def test_products_tool_json(self):
        from bim_mcp import server as S

        out = json.loads(S.bim_aktuel_products(query="yağ", sort="price_asc", limit=5))
        self.assertIn("products", out)
        self.assertGreater(len(out["products"]), 0)
        prices = [p["price_try"] for p in out["products"]]
        self.assertEqual(prices, sorted(prices))


if __name__ == "__main__":
    unittest.main()
