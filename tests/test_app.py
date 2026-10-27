"""End-to-end checks for Workshop Timer, run in headless Chromium.

Run locally:  pip install -r tests/requirements.txt && playwright install chromium && pytest
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DODO = "https://live.dodopayments.com/**"


def state(page):
    return page.evaluate("({running, finished, remaining, title: document.title})")


# ---------------------------------------------------------------- basics

def test_loads_and_counts_down(app):
    app.keyboard.press("Space")
    app.wait_for_timeout(1300)
    s = state(app)
    assert s["running"] and s["remaining"] < 600
    assert s["title"].endswith("· Timer")


def test_all_themes_and_modes_render(app):
    ids = app.evaluate("THEMES.map(t => t.id)")
    assert len(ids) >= 20
    app.evaluate("LICENSE_OK = true; start()")
    for tid in ids:
        app.evaluate(f"st.theme = '{tid}'; applyTheme(); render()")
        app.wait_for_timeout(150)
    for mode in ["swToggle", "clockToggle", "pomodoroToggle", "countdownToggle"]:
        app.evaluate(f"document.getElementById('{mode}').click()")
        app.wait_for_timeout(200)


def test_service_worker_registers(app):
    scope = app.evaluate(
        "Promise.race([navigator.serviceWorker.ready.then(r => r.scope),"
        " new Promise(r => setTimeout(() => r(null), 5000))])"
    )
    assert scope, "sw.js did not register"


# ---------------------------------------------------------------- refresh safety

def test_running_countdown_survives_refresh(app):
    app.evaluate("setDuration(600); start()")
    app.wait_for_timeout(1500)
    app.reload()
    app.wait_for_timeout(800)
    s = state(app)
    assert s["running"]
    assert 590 < s["remaining"] < 599


def test_paused_countdown_survives_refresh(app):
    app.evaluate("setDuration(600); start()")
    app.wait_for_timeout(1600)
    app.evaluate("pause()")
    before = state(app)["remaining"]
    app.reload()
    app.wait_for_timeout(800)
    s = state(app)
    assert not s["running"]
    assert abs(s["remaining"] - before) < 0.01


def test_countdown_that_ran_out_while_closed_shows_finished(app):
    app.evaluate("setDuration(300)")
    app.evaluate(
        "localStorage.setItem(LS.run, JSON.stringify({v:1, at:Date.now()-60000, running:true,"
        " finished:false, remaining:300, deadline:Date.now()-5000, duration:300,"
        " sw:false, swStart:0, swAccum:0}))"
    )
    app.evaluate("runFrozen = true")  # keep the planted snapshot through the reload
    app.reload()
    app.wait_for_timeout(800)
    s = state(app)
    assert s["finished"] and not s["running"] and s["remaining"] == 0


def test_running_stopwatch_survives_refresh(app):
    app.evaluate("document.getElementById('swToggle').click()")
    app.evaluate("start()")
    app.wait_for_timeout(2200)
    app.reload()
    app.wait_for_timeout(800)
    s = state(app)
    assert s["running"] and s["remaining"] >= 2


def test_reset_timer_is_not_restored(app):
    app.evaluate("setDuration(600); start()")
    app.wait_for_timeout(1200)
    app.evaluate("reset()")
    app.reload()
    app.wait_for_timeout(800)
    s = state(app)
    assert not s["running"] and s["remaining"] == 600


# ---------------------------------------------------------------- settings file

def test_settings_file_round_trip(app, browser, tmp_path):
    app.evaluate(
        "st.label = 'Sprint Day 2'; st.theme = 'paper'; setDuration(420);"
        " localStorage.setItem(LS.logo, 'data:image/png;base64,iVBORw0KGgo=')"
    )
    app.click("#btnSettings")
    app.wait_for_timeout(400)
    app.click("#tab-timer")
    app.click("#backupDetails summary")
    app.locator("#exportBtn").scroll_into_view_if_needed()
    with app.expect_download() as dl:
        app.click("#exportBtn")
    path = tmp_path / "settings.json"
    dl.value.save_as(path)
    data = json.loads(path.read_text())
    assert data["app"] == "workshoptimers.com"
    assert data["settings"]["label"] == "Sprint Day 2"

    # load it into a completely separate browser profile
    ctx = browser.new_context()
    ctx.add_init_script("try{localStorage.setItem('wt_onboarded_v1','1')}catch(e){}")
    other = ctx.new_page()
    other.goto(f"{app.url_base}/index.html")
    other.wait_for_timeout(800)
    with other.expect_navigation():
        other.set_input_files("#importFile", str(path))
    other.wait_for_timeout(800)
    got = other.evaluate("[st.label, st.duration, st.theme, !!localStorage.getItem(LS.logo)]")
    ctx.close()
    assert got == ["Sprint Day 2", 420, "paper", True]


def test_bad_settings_file_is_rejected(app, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"hello": 1}')
    before = app.evaluate("st.label")
    app.set_input_files("#importFile", str(bad))
    app.wait_for_timeout(400)
    assert "doesn't look like" in app.evaluate("document.getElementById('importMsg').textContent")
    assert app.evaluate("st.label") == before


# ---------------------------------------------------------------- free vs Pro

def test_voice_is_free_but_fonts_colours_and_logo_are_pro(app):
    assert app.evaluate("isPro()") is False
    app.click("#btnSettings")
    app.click("#tab-sound")
    app.check("#voiceToggle")
    app.check("#voice2minToggle")
    app.check("#voiceHalfToggle")
    app.evaluate("localStorage.setItem(LS.logo, 'data:image/png;base64,iVBORw0KGgo='); applyBranding()")
    locked = app.evaluate(
        "['fontSelect','fontFile','customWeight','accentInput','bgInput','bgToggle','logoInput']"
        ".map(id => document.getElementById(id).disabled)"
    )
    assert all(locked), locked
    # saved picks are kept but not applied for free users
    app.evaluate("st.font='windsor'; st.accent='#00aa55'; st.accentCustom=true; st.useBg=true; st.bg='#123456'; applyTheme()")
    free = app.evaluate(
        "({font: getComputedStyle(document.documentElement).getPropertyValue('--font'),"
        " accent: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim(),"
        " bg: document.body.style.getPropertyValue('--bg')})"
    )
    assert "Fraunces" not in free["font"] and free["accent"] == "#d5442f" and free["bg"] == ""
    got = app.evaluate(
        "({voice: [st.voice, st.voice2min, st.voiceHalf], logo: getComputedStyle(elLogo).display,"
        " proTags: [...document.querySelectorAll('.pro-tag')].length})"
    )
    assert got["voice"] == [True, True, True]
    assert got["logo"] == "none"
    assert got["proTags"] == 8  # more-themes heading, colours & logo group, brand switch, colour variants, font, accent, background, logo
    # unlocking applies them
    app.evaluate("LICENSE_OK = true; applyProLocks(); applyTheme()")
    pro = app.evaluate(
        "({font: getComputedStyle(document.documentElement).getPropertyValue('--font'),"
        " accent: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim(),"
        " bg: document.body.style.getPropertyValue('--bg'), off: document.getElementById('fontSelect').disabled})"
    )
    assert "Fraunces" in pro["font"] and pro["accent"] == "#00aa55" and pro["bg"] == "#123456" and not pro["off"]
    app.evaluate("applyBranding()")
    assert app.evaluate("getComputedStyle(elLogo).display") == "block"


def test_voice_alert_fires_for_free_users(app):
    said = app.evaluate(
        "new Promise(res => { const out = []; window.announce = announce = t => out.push(t);"
        " st.voice = true; st.muted = false; setDuration(31); start();"
        " setTimeout(() => { pause(); res(out); }, 1700); })"
    )
    assert "Attention please. Thirty seconds remaining." in said


def test_pro_themes_stay_locked_for_free_users(app):
    pro = app.evaluate("THEMES.find(t => t.pro).id")
    app.evaluate(f"st.theme = '{pro}'; save()")
    app.reload()
    app.wait_for_timeout(800)
    assert app.evaluate("st.theme") != pro


def test_pro_section_matches_whether_sales_are_open(app):
    sales_open = app.evaluate("SALES_OPEN")
    ui = app.evaluate(
        "({buy: getComputedStyle(document.getElementById('btnTrial')).display,"
        " keyBox: getComputedStyle(document.getElementById('licenseBox')).display,"
        " status: document.getElementById('trialStatus').textContent})"
    )
    app.evaluate("previewTheme(THEMES.find(t => t.pro).id)")
    badge = app.evaluate("document.getElementById('previewBadge').textContent")
    if sales_open:
        assert ui["buy"] != "none" and ui["keyBox"] != "none"
    else:
        assert ui["buy"] == "none" and ui["keyBox"] == "none"
        assert "Pro coming soon" in badge


# ---------------------------------------------------------------- Dodo licence keys (mocked)

@pytest.mark.parametrize(
    "dodo, keeps_pro",
    [("valid", True), ("invalid", False), ("404", False), ("500", True), ("offline", True)],
)
def test_stored_licence_is_only_revoked_on_a_definite_no(browser, base_url, dodo, keeps_pro):
    ctx = browser.new_context()
    page = ctx.new_page()
    sent = []

    def handle(route):
        sent.append(json.loads(route.request.post_data or "{}"))
        if dodo == "offline":
            route.abort()
        elif dodo in ("404", "500"):
            route.fulfill(status=int(dodo), body="{}")
        else:
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"valid": dodo == "valid"}))

    page.route(DODO, handle)
    page.add_init_script(
        "localStorage.setItem('wt_onboarded_v1','1');"
        "localStorage.setItem('wt_license_v1', JSON.stringify({key:'K-1', activationId:'lki_1'}))"
    )
    page.goto(f"{base_url}/index.html")
    page.wait_for_timeout(1200)
    pro = page.evaluate("isPro()")
    kept = page.evaluate("localStorage.getItem(LS.license) !== null")
    ctx.close()
    assert sent and sent[0] == {"license_key": "K-1", "license_key_instance_id": "lki_1"}
    assert pro is keeps_pro and kept is keeps_pro


def test_activation_sends_only_the_key_and_a_plain_label(app):
    sent = []

    def handle(route):
        body = json.loads(route.request.post_data or "{}")
        sent.append(body)
        if body.get("license_key") == "FULL":
            route.fulfill(status=422, body="{}")
        else:
            route.fulfill(status=201, content_type="application/json",
                          body=json.dumps({"id": "lki_9", "customer": {"email": "x@example.com"}}))

    app.route(DODO, handle)
    ok = app.evaluate("unlockWithKey('ABC')")
    assert ok == {"ok": True, "key": "ABC", "activationId": "lki_9"}
    assert set(sent[0]) == {"license_key", "name"}
    assert re.fullmatch(r"Workshop Timer · activated \d{4}-\d{2}-\d{2}", sent[0]["name"])
    assert app.evaluate("unlockWithKey('FULL')") == {"ok": False, "reason": "limit"}


# ---------------------------------------------------------------- accessibility

def test_keyboard_and_screen_reader_basics(app):
    labels = app.evaluate(
        "['btnAppearance','btnMute','btnFull','btnReset','btnPlus30','display']"
        ".map(id => document.getElementById(id).getAttribute('aria-label'))"
    )
    assert all(labels), labels
    app.focus("#display")
    app.keyboard.press("Enter")
    app.wait_for_timeout(200)
    assert app.evaluate("document.activeElement.id") == "timeInput"
    app.keyboard.press("Escape")
    app.evaluate("document.activeElement.blur(); setDuration(5); start()")
    app.wait_for_timeout(6200)
    assert app.evaluate("document.getElementById('srStatus').textContent") == "Time's up"


# ---------------------------------------------------------------- legal pages

@pytest.mark.parametrize("page_name", ["impressum", "datenschutz", "agb", "widerruf", "license"])
def test_legal_pages_are_complete(browser, base_url, page_name):
    ctx = browser.new_context()
    page = ctx.new_page()
    resp = page.goto(f"{base_url}/{page_name}.html")
    text = page.inner_text("body")
    ctx.close()
    assert resp.ok
    assert "Jeffrey Humble" in text
    for stale in ["Placeholder", "Platzhalter", "Polar", "ec.europa.eu/consumers/odr", "trading name"]:
        assert stale not in text, f"{page_name}.html still mentions {stale!r}"


# ---------------------------------------------------------------- favicon

@pytest.mark.parametrize("page_name", ["index", "impressum", "datenschutz", "agb", "widerruf", "license"])
def test_every_page_links_a_working_favicon(browser, base_url, page_name):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(f"{base_url}/{page_name}.html")
    hrefs = page.evaluate("[...document.querySelectorAll('link[rel~=icon],link[rel=apple-touch-icon]')].map(l => l.href)")
    codes = [ctx.request.get(h).status for h in hrefs]
    ctx.close()
    assert len(hrefs) == 3 and set(codes) == {200}


# ---------------------------------------------------------------- Pro build stays private

def test_repo_ships_only_the_locked_build():
    """The public repo and the published site must never carry the unlocked Pro build."""
    assert "const PRO_UNLOCKED = false;" in (ROOT / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"^const PRO_UNLOCKED = true;", (ROOT / "index.html").read_text(encoding="utf-8"), re.M)
    stray = [p.name for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts
             and (p.name.endswith("-pro.html") or "pro-bundle" in p.parts or p.suffix == ".zip")]
    assert not stray, f"Pro files found in the repository: {stray}"
    workflow = (ROOT / ".github/workflows/test-and-deploy.yml").read_text(encoding="utf-8")
    assert "cp *.html" not in workflow, "the deploy step must list files, not use a wildcard"


def test_pro_build_differs_by_one_line_and_lands_outside_the_repo(tmp_path):
    import subprocess
    import sys
    out = tmp_path / "pro-bundle"
    subprocess.run([sys.executable, "-I", str(ROOT / "scripts/build_pro.py"), str(out)], check=True)
    free = (ROOT / "index.html").read_text(encoding="utf-8").splitlines()
    pro = (out / "workshop-timer-pro.html").read_text(encoding="utf-8").splitlines()
    assert len(free) == len(pro)
    diff = [(a, b) for a, b in zip(free, pro) if a != b]
    assert diff == [("const PRO_UNLOCKED = false;", "const PRO_UNLOCKED = true;")]
    refused = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/build_pro.py"), str(ROOT / "inside")])
    assert refused.returncode != 0 and not (ROOT / "inside").exists()


def test_licence_header_and_settings_line_name_the_new_licence(app):
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>\n<!--") and "Elastic License 2.0" in html[:600] and "Jeffrey Humble" in html[:600]
    assert "MIT licence" not in html.split("<script>")[0]
    assert "Elastic License 2.0" in app.text_content("#settings")  # sits under Help & about


# ---------------------------------------------------------------- settings panel (tabs, duration, confirm)

def test_new_time_while_running_asks_first(app):
    app.keyboard.press("Space")
    app.wait_for_timeout(300)
    app.locator("#presets button.preset").nth(3).click()  # 5 min
    assert app.evaluate("document.getElementById('confirmDialog').open")
    app.click("#confirmKeep")
    assert app.evaluate("[running, st.duration]") == [True, 600]
    app.locator("#presets button.preset").nth(3).click()  # 5 min
    app.click("#confirmGo")
    assert app.evaluate("[running, st.duration, document.getElementById('confirmDialog').open]") == [False, 300, False]


def test_preset_when_stopped_does_not_ask(app):
    app.locator("#presets button.preset").nth(3).click()  # 5 min
    assert app.evaluate("[st.duration, document.getElementById('confirmDialog').open]") == [300, False]


def test_mode_change_while_running_asks_first(app):
    app.click("#btnSettings")
    app.click("#tab-timer")
    app.evaluate("start(false)")
    app.wait_for_timeout(200)
    app.click("label.mode-choice:has(#swToggle)")
    assert app.evaluate("document.getElementById('confirmDialog').open")
    app.click("#confirmKeep")
    assert app.evaluate("[running, st.stopwatch, document.getElementById('swToggle').checked]") == [True, False, False]
    app.click("label.mode-choice:has(#swToggle)")
    app.click("#confirmGo")
    assert app.evaluate("st.stopwatch") is True


def test_duration_field_sets_the_time_and_rejects_nonsense(app):
    app.click("#btnSettings")
    app.click("#tab-timer")
    app.fill("#durationSetting", "nonsense")
    app.click("#applyDuration")
    assert app.is_visible("#durationError")
    app.fill("#durationSetting", "12:30")
    app.click("#applyDuration")
    assert app.evaluate("[st.duration, remaining]") == [750, 750]
    assert not app.is_visible("#durationError")


def test_session_name_field_renames_the_timer(app):
    app.click("#btnSettings")
    app.click("#tab-timer")
    app.fill("#sessionLabel", "Retro, team blue")
    assert app.evaluate("[st.label, st.labelCustom, elLabel.textContent]") == ["Retro, team blue", True, "Retro, team blue"]


def test_theme_picker_shows_thumbnails_and_separates_pro(app):
    app.click("#btnSettings")
    app.click("#tab-look")
    cards = app.evaluate(
        "[...document.querySelectorAll('#themeRow .theme-card')].map(b => [b.dataset.theme, b.classList.contains('locked'),"
        " (b.querySelector('img') || {}).src ? 1 : 0])"
    )
    assert len(cards) == 23 and all(c[2] == 1 for c in cards), cards       # every theme has its thumbnail
    assert [c[0] for c in cards[:3]] == ["disc", "midnight", "paper"]      # included themes come first
    assert not any(c[1] for c in cards[:3]) and all(c[1] for c in cards[3:])
    app.click('#themeRow .theme-card[data-theme="nixie"]')                 # a locked theme previews live
    assert app.evaluate("[PV.id, st.theme]") == ["nixie", "disc"]


def test_pro_can_hide_or_show_the_brand(app):
    assert app.evaluate("document.getElementById('tbBrand').hidden") is False
    app.evaluate("LICENSE_OK = true; applyBranding(); refreshSettings()")
    assert app.evaluate("document.getElementById('tbBrand').hidden") is True
    app.click("#btnSettings")
    app.click("#tab-look")
    app.click("#brandDetails summary")
    app.click("#brandToggle")
    assert app.evaluate("[st.showBrand, document.getElementById('tbBrand').hidden]") == [True, False]


def test_removing_the_licence_takes_two_clicks(app):
    app.evaluate("LICENSE_OK = true; localStorage.setItem(LS.license, JSON.stringify({key:'K-1', activationId:'lki_1'}));"
                 " refreshSettings(); applyProLocks()")
    app.evaluate("(()=>{ const rl = document.getElementById('removeLicenseWrap'); rl.style.display = 'block'; })()")
    app.click("#btnSettings")
    app.locator("#removeLicense").scroll_into_view_if_needed()
    app.click("#removeLicense")
    assert app.evaluate("localStorage.getItem(LS.license) !== null")    # first click only asks
    assert app.inner_text("#removeLicense") == "Click again to remove"
