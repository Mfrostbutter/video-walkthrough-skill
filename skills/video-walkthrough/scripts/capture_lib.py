"""Shared Playwright capture helpers for the ffmpeg walkthrough pipeline. Import from a per-project capture.py.

A scene is a function fn(sc): it navigates off camera, calls start(sc) when the picture is ready, then paces
its actions with sc.at(frac) against the scene's VO duration. Capture.record() wraps it: one browser context
per scene, video to captures/<cut>/raw/scene_NN.webm, trimmed at start() and transcoded to
captures/<cut>/scene_NN.mp4, with captures/<cut>/clips.json merged after every scene.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

W, H = 1920, 1080
VO_LEAD, TAIL = 0.6, 2.0  # seconds before the VO starts; seconds held after it ends (assembly uses its own TAIL)

CURSOR_SVG = ('<svg width="22" height="22" viewBox="0 0 24 24"><path d="M5 3l14 8-6 1.5L16 20l-3 1-3-7.5L5 17z" '
              'fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>')


def init_js(hide_css: str = "", preseed: dict | None = None) -> str:
    """Init script for every page in a context: localStorage pre-seed, hide CSS, fake cursor following the mouse."""
    return """
(() => {
  const seed = __PRESEED__;
  try { for (const [k, v] of Object.entries(seed)) localStorage.setItem(k, v); } catch (e) {}
  const css = __HIDE_CSS__;
  if (css) {
    const style = document.createElement('style'); style.textContent = css;
    const addStyle = () => document.head && document.head.appendChild(style);
    document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', addStyle) : addStyle();
  }
  const c = document.createElement('div');
  c.id = '__cur';
  c.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;z-index:2147483647;pointer-events:none;'
    + 'transform:translate(-3px,-2px);transition:transform .08s;';
  c.innerHTML = __CURSOR__;
  const add = () => document.body && document.body.appendChild(c);
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', add) : add();
  window.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  window.addEventListener('mousedown', () => { c.style.transform = 'translate(-3px,-2px) scale(.8)'; }, true);
  window.addEventListener('mouseup', () => { c.style.transform = 'translate(-3px,-2px) scale(1)'; }, true);
})();
""".replace("__PRESEED__", json.dumps(preseed or {})).replace("__HIDE_CSS__", json.dumps(hide_css)).replace("__CURSOR__", json.dumps(CURSOR_SVG))


class Scene:
    """Pacing helper. at(frac) waits until frac of the VO has elapsed since start(); glide/click/type move a visible cursor."""

    def __init__(self, page, vo_seconds: float):
        self.page, self.t0, self.vo = page, time.time(), vo_seconds

    def at(self, frac: float):
        t = VO_LEAD + frac * self.vo
        rem = t - (time.time() - self.t0)
        if rem > 0:
            self.page.wait_for_timeout(int(rem * 1000))

    def glide(self, x: int, y: int, steps: int = 28):
        self.page.mouse.move(x, y, steps=steps)
        self.page.wait_for_timeout(250)

    def glide_to(self, sel: str, dx: int = 24, dy=None):
        loc = self.page.locator(sel)
        if loc.count() == 0:
            print(f"    (glide_to: no match for {sel})", flush=True)
            return
        box = loc.first.bounding_box()
        if box:
            self.glide(int(box["x"] + min(dx, box["width"] / 2)), int(box["y"] + (dy if dy is not None else box["height"] / 2)))

    def click(self, sel: str, dx: int = 24):
        self.glide_to(sel, dx=dx)
        loc = self.page.locator(sel)
        if loc.count():
            loc.first.click()
        else:
            print(f"    (click: no match for {sel})", flush=True)

    def type(self, sel: str, text: str, delay: int = 60):
        self.click(sel)
        self.page.keyboard.type(text, delay=delay)

    def hold_min(self):
        rem = VO_LEAD + self.vo + TAIL - (time.time() - self.t0)
        if rem > 0:
            self.page.wait_for_timeout(int(rem * 1000))


def start(sc: Scene):
    """Mark the on-camera start: everything before (login, navigation) is trimmed from the clip."""
    sc.wall0 = sc.t0
    sc.t0 = time.time()


def hide_cursor(page):
    page.evaluate("const c=document.getElementById('__cur'); if (c) c.style.display='none'")


def dismiss(page, selectors=()):
    """Click first-run modals away by their buttons; each selector gets 1.2 s and is skipped if absent."""
    for sel in selectors:
        try:
            page.locator(sel).first.click(timeout=1200)
            page.wait_for_timeout(500)
        except Exception:
            pass


def open_page(page, login, url: str, settle: float = 2.2, wait_for: str | None = None, dismiss_selectors=()):
    """Login and navigation off camera. Waits for the post-login redirect to settle, then for the page's anchor element."""
    login(page)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(800)
    for attempt in range(3):
        page.goto(url)
        try:
            if wait_for:
                page.wait_for_selector(wait_for, timeout=15000)
            break
        except Exception:
            print(f"    (open_page: {wait_for} not found, retry {attempt + 1})", flush=True)
    page.wait_for_timeout(int(settle * 1000))
    dismiss(page, dismiss_selectors)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


class Capture:
    """One cut's recorder. reset(sid, kind) runs off camera before each scene; scenes is [(id, kind, fn)]."""

    def __init__(self, root: Path, cut: str = "main", hide_css: str = "", preseed: dict | None = None,
                 reset=None, color_scheme: str = "dark"):
        self.root, self.cut = Path(root), cut
        self.vo = {s["id"]: s["duration"] for s in json.loads((self.root / "vo" / cut / "manifest.json").read_text())["scenes"]}
        self.cap = self.root / "captures" / cut
        self.raw = self.cap / "raw"
        self.scenes_html = self.root / "scenes"
        self.init_js = init_js(hide_css, preseed)
        self.reset = reset
        self.color_scheme = color_scheme

    def card(self, name: str):
        """A scene that shows scenes/<name>.html for the VO; the card animates itself with CSS."""
        def fn(sc):
            sc.page.goto((self.scenes_html / f"{name}.html").as_uri())
            sc.page.wait_for_timeout(500)
            hide_cursor(sc.page)
            start(sc)
        return fn

    def record(self, pw, sid: str, kind: str, fn):
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1,
                                  record_video_dir=str(self.raw), record_video_size={"width": W, "height": H},
                                  color_scheme=self.color_scheme)
        ctx.add_init_script(self.init_js)
        page = ctx.new_page()
        page.set_default_timeout(45_000)
        page.mouse.move(1180, 620)
        sc = Scene(page, self.vo[sid])
        trim = 0.0
        try:
            if self.reset:
                self.reset(sid, kind)
            fn(sc)
            trim = sc.t0 - sc.wall0 if hasattr(sc, "wall0") else 0.0
            sc.hold_min()
        finally:
            video = page.video
            ctx.close()
            browser.close()
        src = Path(video.path())
        dst = self.raw / f"scene_{sid}.webm"
        if dst.exists():
            dst.unlink()
        src.rename(dst)
        print(f"  scene {sid}: {time.time() - sc.t0:.0f}s on camera, trim {trim:.1f}s -> {dst.name}", flush=True)
        return dst, trim

    def to_mp4(self, src: Path, trim_start: float = 0.0) -> Path:
        dst = self.cap / (src.stem + ".mp4")
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        if trim_start > 0:
            cmd += ["-ss", f"{trim_start:.2f}"]
        cmd += ["-i", str(src), "-r", "30", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                "-vf", "scale=1920:1080:flags=lanczos", "-an", str(dst)]
        subprocess.run(cmd, check=True)
        return dst

    def run(self, scenes, only=()):
        """Record the listed scenes (all, or the ids in `only`), merging clips.json after each one."""
        from playwright.sync_api import sync_playwright

        self.raw.mkdir(parents=True, exist_ok=True)
        manifest = self.cap / "clips.json"
        with sync_playwright() as pw:
            for sid, kind, fn in scenes:
                if only and sid not in only:
                    continue
                if sid not in self.vo:
                    sys.exit(f"scene {sid} has no VO in vo/{self.cut}/manifest.json; run make_vo first")
                print(f"recording {self.cut} scene {sid} {kind} (vo {self.vo[sid]}s)", flush=True)
                raw, trim = self.record(pw, sid, kind, fn)
                mp4 = self.to_mp4(raw, trim)
                existing = json.loads(manifest.read_text()) if manifest.exists() else {}
                existing[sid] = {"clip": str(mp4), "duration": round(duration(mp4), 2), "kind": kind}
                manifest.write_text(json.dumps(existing, indent=2))
                print(f"  -> {mp4.name} {existing[sid]['duration']}s", flush=True)
        print(f"wrote {manifest}", flush=True)
