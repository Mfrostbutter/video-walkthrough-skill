"""Render lower-third PNGs (alpha) per cut and the silent outro clip.

IN: scenes/lower.html (reads ?text= and ?kicker=), scenes/outro.html, scenes/lower_thirds.json {cut: {scene_id: text}}.
OUT: overlays/<cut>/lower_NN.png, overlays/outro.png, captures/<cut>/outro.mp4 (5 s, silent, 30 fps).
"""
import json
import subprocess
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SCENES = ROOT / "scenes"
LT = json.loads((SCENES / "lower_thirds.json").read_text())
KICKER = json.loads((SCENES / "lower_thirds.json").read_text()).get("_kicker")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    for cut, items in LT.items():
        if cut.startswith("_"):
            continue
        out = ROOT / "overlays" / cut
        out.mkdir(parents=True, exist_ok=True)
        for sid, text in items.items():
            q = {"text": text}
            if KICKER:
                q["kicker"] = KICKER
            page.goto((SCENES / "lower.html").as_uri() + "?" + urlencode(q))
            page.wait_for_timeout(400)
            page.locator("#lt").screenshot(path=out / f"lower_{sid}.png", omit_background=True)
        print(f"{cut}: {len(items)} lower thirds")
    page.goto((SCENES / "outro.html").as_uri()); page.wait_for_timeout(1200)
    png = ROOT / "overlays" / "outro.png"
    page.screenshot(path=png)
    for cut in LT:
        if cut.startswith("_"):
            continue
        dst = ROOT / "captures" / cut / "outro.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-t", "5", "-r", "30",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080", str(dst)], check=True)
    b.close()
print("overlays rendered")
