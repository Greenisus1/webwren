import importlib.util, json, os, tempfile, time, unittest, urllib.request

HOME = tempfile.mkdtemp()
os.environ["WEBWREN_HOME"] = HOME
os.environ["WEBWREN_PORT"] = "18099"
spec = importlib.util.spec_from_file_location(
    "webwren", os.path.join(os.path.dirname(__file__), "webwren.py"))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class TestPages(unittest.TestCase):
    def test_ensure_site(self):
        w.ensure_site()
        self.assertIn("index.html", w.pages())
        body = open(w.page_path("index.html")).read()
        self.assertIn("It works", body)

    def test_new_page(self):
        self.assertTrue(w.new_page("about.html"))
        self.assertFalse(w.new_page("about.html"))  # exists
        body = open(w.page_path("about.html")).read()
        self.assertIn("<h1>About</h1>", body)

    def test_path_escape_blocked(self):
        w.new_page("../evil.html")
        self.assertFalse(os.path.exists(os.path.join(HOME, "evil.html")))
        self.assertIn("evil.html", w.pages())  # created inside site dir

    def test_cfg(self):
        w.save_cfg({"port": 18099})
        self.assertEqual(w.load_cfg()["port"], 18099)


class TestServer(unittest.TestCase):
    def test_start_serve_stop(self):
        w.ensure_site()
        w.new_page("hello.html")
        ok, info = w.start_server(18099)
        self.assertTrue(ok, info)
        try:
            idx = urllib.request.urlopen(
                "http://127.0.0.1:18099/", timeout=5).read().decode()
            self.assertIn("It works", idx)
            page = urllib.request.urlopen(
                "http://127.0.0.1:18099/hello.html", timeout=5).read().decode()
            self.assertIn("<h1>Hello</h1>", page)
            try:
                urllib.request.urlopen("http://127.0.0.1:18099/nope.html",
                                       timeout=5)
                self.fail("expected 404")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 404)
        finally:
            self.assertTrue(w.stop_server())
        self.assertIsNone(w.server_pid())


if __name__ == "__main__":
    unittest.main()
