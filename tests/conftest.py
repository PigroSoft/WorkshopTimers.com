"""Shared fixtures: serve the repo over local HTTP and drive it with headless Chromium."""
import functools
import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def base_url():
    handler = functools.partial(_QuietHandler, directory=str(ROOT))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
        httpd.shutdown()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        # software WebGL so the animated themes render on CI machines without a GPU
        b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        yield b
        b.close()


@pytest.fixture
def app(browser, base_url):
    """A fresh browser profile with the app open and first-run onboarding skipped.

    Fails the test if the page throws any uncaught JavaScript error."""
    ctx = browser.new_context(accept_downloads=True)
    ctx.add_init_script("try{localStorage.setItem('wt_onboarded_v1','1')}catch(e){}")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.url_base = base_url
    page.errors = errors
    page.goto(f"{base_url}/index.html")
    page.wait_for_timeout(800)
    yield page
    ctx.close()
    assert not errors, f"JavaScript errors on the page: {errors}"
