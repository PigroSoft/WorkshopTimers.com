#!/usr/bin/env python3
"""Regenerate the theme thumbnails embedded in index.html.

Each theme is rendered at 5:00 in headless Chromium with the buttons, panel and
top bar hidden, shrunk to a small WebP and written into the THEME_THUMBS block
of index.html, so the app stays one self-contained file that works offline.

    pip install playwright pillow && playwright install chromium
    python3 scripts/make_thumbs.py
"""
import base64
import functools
import http.server
import io
import re
import socketserver
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
SIZE = (256, 160)          # 16:10, shown at about half that size in the panel
QUALITY = 62
HIDE = "#topBar,#controls,#settings,#previewBadge,#logo,#toasts{display:none!important}"


def main() -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.log_message = lambda *a, **k: None
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
    thumbs = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})  # laptop-sized layout
        ctx.add_init_script("try{localStorage.setItem('wt_onboarded_v1','1')}catch(e){}")
        page = ctx.new_page()
        page.goto(url)
        page.wait_for_timeout(800)
        page.add_style_tag(content=HIDE)
        for tid in page.evaluate("THEMES.map(t => t.id)"):
            page.evaluate(
                "id => { LICENSE_OK = true; cancelPreview(); st.theme = id; st.appearance = null;"
                " st.font = (THEMES.find(x => x.id === id) || {}).font || 'helvetica';"
                " st.stopwatch = st.clock = st.pomodoro = false; st.duration = 300; remaining = 300;"
                " applyTheme(); render(); }", tid)
            page.wait_for_timeout(1200)
            if tid == "bounce":  # park the bouncing digits in the middle for the picture
                page.evaluate("() => { const r = elBounceTime.getBoundingClientRect(); BOUNCE.vx = BOUNCE.vy = 0;"
                              " BOUNCE.x = (innerWidth - r.width) / 2; BOUNCE.y = (innerHeight - r.height) / 2;"
                              " elBounceTime.style.transform = `translate(${BOUNCE.x}px,${BOUNCE.y}px)`; }")
                page.wait_for_timeout(300)
            # laptop-sized layout, cropped to the central 85% so the artwork fills the card
            img = Image.open(io.BytesIO(page.screenshot())).convert("RGB").crop((96, 60, 1184, 740)).resize(SIZE, Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "WEBP", quality=QUALITY, method=6)
            thumbs[tid] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
            print(f"{tid:12s} {len(buf.getvalue()):6d} bytes")
        browser.close()
    server.shutdown()

    body = "".join(f'  {tid}:"{data}",\n' for tid, data in thumbs.items())
    html = INDEX.read_text(encoding="utf-8")
    new, n = re.subn(r"const THEME_THUMBS = \{.*?\};\n// END THEME_THUMBS",
                     lambda m: "const THEME_THUMBS = {\n" + body + "};\n// END THEME_THUMBS", html, flags=re.S)
    if n != 1:
        raise SystemExit("THEME_THUMBS block not found in index.html")
    INDEX.write_text(new, encoding="utf-8")
    print(f"wrote {len(thumbs)} thumbnails, {sum(len(v) for v in thumbs.values()) // 1024} KB")


if __name__ == "__main__":
    main()
