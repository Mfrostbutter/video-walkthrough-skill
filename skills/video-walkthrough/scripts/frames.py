"""Review frames. Default: 4 frames per clip at 10/40/70/95 percent of the VO, tiled 2x2, one grid per scene.
With FINAL=1: six frames from the assembled cut (out/<cut>-<quality>.mp4) in one 3x2 grid.

IN: CUT env (default main), captures/<cut>/clips.json, vo/<cut>/manifest.json; FINAL=1 plus QUALITY env for the cut grid.
OUT: review/<cut>/scene_NN.png, or review/<cut>/cut-<quality>.png
"""
import json
import os
import subprocess
from pathlib import Path

CUT = os.environ.get("CUT", "main")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "review" / CUT
OUT.mkdir(parents=True, exist_ok=True)
VO_LEAD = 0.6


def grab(src: Path, t: float, dst: Path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                    "-vf", "scale=960:540", str(dst)], check=True)


def tile(frames, cols, dst: Path):
    rows = (len(frames) + cols - 1) // cols
    layout = "|".join(f"{'+'.join(['w0'] * (i % cols)) or 0}_{'+'.join(['h0'] * (i // cols)) or 0}" for i in range(len(frames)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *sum((["-i", str(f)] for f in frames), []),
                    "-filter_complex", "".join(f"[{i}:v]" for i in range(len(frames))) + f"xstack=inputs={len(frames)}:layout={layout}[v]",
                    "-map", "[v]", str(dst)], check=True)


if os.environ.get("FINAL"):
    quality = os.environ.get("QUALITY", "review")
    src = ROOT / "out" / f"{CUT}-{quality}.mp4"
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                                 capture_output=True, text=True, check=True).stdout.strip())
    times = [3, total * 0.12, total * 0.35, total * 0.6, total * 0.85, total - 2.5]
    tmp = []
    for i, t in enumerate(times):
        f = OUT / f"_cut_{i}.png"; grab(src, t, f); tmp.append(f)
    tile(tmp, 3, OUT / f"cut-{quality}.png")
    for f in tmp:
        f.unlink()
    print(f"cut frames at {[round(t, 1) for t in times]} -> review/{CUT}/cut-{quality}.png")
else:
    VO = {s["id"]: s for s in json.loads((ROOT / "vo" / CUT / "manifest.json").read_text())["scenes"]}
    CLIPS = json.loads((ROOT / "captures" / CUT / "clips.json").read_text())
    only = set(os.environ.get("ONLY", "").split()) if os.environ.get("ONLY") else None
    for sid, clip in sorted(CLIPS.items()):
        if only and sid not in only or sid not in VO:
            continue
        d = VO[sid]["duration"]
        times = [VO_LEAD + f * d for f in (0.10, 0.40, 0.70, 0.95)]
        tmp = []
        for i, t in enumerate(times):
            f = OUT / f"_{sid}_{i}.png"; grab(Path(clip["clip"]), t, f); tmp.append(f)
        tile(tmp, 2, OUT / f"scene_{sid}.png")
        for f in tmp:
            f.unlink()
        print(f"scene {sid}: frames at {[round(t, 1) for t in times]} -> review/{CUT}/scene_{sid}.png")
