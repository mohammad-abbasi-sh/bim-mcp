"""Offline tests for bim_mcp — recorded BİM fixtures, no network.

Fixtures recorded 2026-11-10 from bim.com.tr (plain HTTP 200):
- home.html: homepage (Aktüel/İndirim date menus)
- aktuel.html: Aktüel products, default week (key 1697, "03 Kasım Salı")
- detail.html: product detail (aycicek-yagi-pet-sise-26-10)
- cesitler.html: product-range page (11 Markalar categories)
- magazalar.html: store-finder page (81-province dropdown)

Run: python -m unittest discover -s tests -v
"""
import os
import unittest

from bim_mcp import bim as B

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


class TestDates(unittest.TestCase):
    def setUp(self):
        self.html = _read("home.html")

    def test_twelve_dates(self):
        dates = B.parse_aktuel_dates(self.html)
        self.assertEqual(len(dates), 12)
        keys = {d["key"] for d in dates}
        self.assertIn("1697", keys)
        self.assertIn("1708", keys)

    def test_first_is_current_aktuel(self):
        dates = B.parse_aktuel_dates(self.html)
        self.assertEqual(dates[0]["key"], "1697")
        self.assertEqual(dates[0]["label"], "03 Kasım Salı")
        self.assertEqual(dates[0]["kind"], "aktuel")

    def test_indirim_kind(self):
        dates = B.parse_aktuel_dates(self.html)
        indirim = [d for d in dates if d["kind"] == "indirim"]
        self.assertEqual(len(indirim), 2)
        self.assertEqual(indirim[0]["label"], "03-30 Kasım")
        self.assertEqual(indirim[1]["label"], "07-13 Kasım")


class TestProducts(unittest.TestCase):
    def setUp(self):
        self.html = _read("aktuel.html")
        self.products = B.parse_products(self.html)

    def test_93_priced_products(self):
        # 95 blocks on the page; 2 are image-only banners (no price).
        self.assertEqual(len(self.products), 93)

    def test_first_product(self):
        p = self.products[0]
        self.assertEqual(p["brand"], "TURNA")
        self.assertEqual(p["name"], "AYÇİÇEK YAĞI PET ŞİŞE")
        self.assertEqual(p["size"], "5 L")
        self.assertEqual(p["price_try"], 429.0)
        self.assertEqual(p["slug"], "aycicek-yagi-pet-sise-26-10")
        self.assertEqual(p["bim_id"], "72460")
        self.assertTrue(p["image_url"].startswith("https://cdn1.bim.com.tr/"))
        self.assertTrue(p["url"].endswith("/aktuel-urunler/aycicek-yagi-pet-sise-26-10/aktuel.aspx"))

    def test_second_product_thousand_separator(self):
        p = self.products[1]
        self.assertEqual(p["brand"], "SÖKE HERGÜN")
        self.assertEqual(p["name"], "BUĞDAY UNU")
        self.assertEqual(p["price_try"], 115.0)

    def test_all_have_name_price_url(self):
        for p in self.products:
            self.assertTrue(p["name"])
            self.assertIsInstance(p["price_try"], float)
            self.assertGreater(p["price_try"], 0)
            self.assertTrue(p["url"].startswith("https://www.bim.com.tr/aktuel-urunler/"))
            self.assertTrue(p["slug"])


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.products = B.parse_products(_read("aktuel.html"))

    def test_yag(self):
        rows = B.search_products(self.products, "yağ")
        self.assertEqual(len(rows), 2)
        for r in rows:
            joined = B._fold(f"{r['brand']} {r['name']} {r['size']}")
            self.assertIn("yağ", joined)

    def test_turkish_case_insensitive(self):
        self.assertEqual(
            len(B.search_products(self.products, "YAĞ")),
            len(B.search_products(self.products, "yağ")),
        )
        self.assertEqual(
            len(B.search_products(self.products, "SÜT")),
            len(B.search_products(self.products, "süt")),
        )

    def test_no_match(self):
        self.assertEqual(B.search_products(self.products, "zzzzqqq"), [])

    def test_empty_query_returns_all(self):
        self.assertEqual(
            len(B.search_products(self.products, "")), len(self.products)
        )


class TestPriceStats(unittest.TestCase):
    def test_stats(self):
        products = B.parse_products(_read("aktuel.html"))
        s = B.price_stats(products)
        self.assertEqual(s["count"], 93)
        self.assertEqual(s["min_try"], 8.75)
        self.assertEqual(s["median_try"], 109.0)
        self.assertAlmostEqual(s["mean_try"], 122.81, places=2)
        self.assertEqual(s["max_try"], 495.0)
        self.assertEqual(len(s["cheapest"]), 5)
        self.assertEqual(len(s["priciest"]), 5)
        self.assertEqual(s["cheapest"][0]["price_try"], 8.75)
        self.assertEqual(s["priciest"][0]["price_try"], 495.0)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            B.price_stats([])


class TestDetail(unittest.TestCase):
    def test_detail(self):
        d = B.parse_product_detail(
            _read("detail.html"), "aycicek-yagi-pet-sise-26-10"
        )
        self.assertEqual(d["name"], "AYÇİÇEK YAĞI PET ŞİŞE")
        self.assertEqual(d["size"], "5 L")
        self.assertEqual(d["price_try"], 429.0)
        self.assertEqual(d["bim_id"], "72460")
        self.assertIn("_buyuk_", d["image_url"])

    def test_detail_no_price_raises(self):
        with self.assertRaises(ValueError):
            B.parse_product_detail("<html></html>", "nope")


class TestCategories(unittest.TestCase):
    def test_eleven_categories(self):
        cats = B.parse_categories(_read("cesitler.html"))
        self.assertEqual(len(cats), 11)
        names = [c["name"] for c in cats]
        self.assertIn("Süt ve Süt Ürünleri", names)
        self.assertIn("İçecekler", names)
        self.assertIn("Gıda Dışı", names)
        self.assertEqual(cats[0]["id"], "1")
        self.assertEqual(cats[0]["slug"], "etli-taze-mamuller")


class TestCities(unittest.TestCase):
    def test_81_provinces(self):
        cities = B.parse_cities(_read("magazalar.html"))
        self.assertEqual(len(cities), 81)
        names = {c["name"] for c in cities}
        self.assertIn("İstanbul", names)
        self.assertIn("Ankara", names)
        self.assertIn("İzmir", names)
        self.assertNotIn("Seçiniz", names)


if __name__ == "__main__":
    unittest.main()
