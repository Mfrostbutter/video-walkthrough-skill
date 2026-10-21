"""Assemble one cut with ffmpeg: per-scene clip + VO + lower third, then concat, then a silent outro card.

IN: CUT env (default main), QUALITY env (review|final), vo/<cut>/manifest.json, captures/<cut>/clips.json,
    overlays/<cut>/lower_NN.png (optional per scene), captures/<cut>/outro.mp4 (optional), scenes/lower_thirds.json.
OUT: out/<cut>-review.mp4 or out/<cut>-final.mp4; per-scene parts in out/work-<cut>/.
A clip opens on the page the voice is about; the VO starts VO_LEAD seconds in; the scene ends TAIL seconds after the VO.
Scene order is the sorted manifest id. A clip shorter than its scene holds its last frame (tpad).
"""
import json
import os
import subprocess
from pathlib import Path

CUT = os.environ.get("CUT", "main")
LT_X = "W-w-64" if os.environ.get("LT_POS", "left") == "right" else "64"  # lower-third side; right clears n8n zoom controls
QUALITY = os.environ.get("QUALITY", "review")
ROOT = Path(__file__).resolve().parent.parent
VO = {s["id"]: s for s in json.loads((ROOT / "vo" / CUT / "manifest.json").read_text())["scenes"]}
CLIPS = json.loads((ROOT / "captures" / CUT / "clips.json").read_text())
OVER = ROOT / "overlays" / CUT
WORK = ROOT / "out" / f"work-{CUT}"
WORK.mkdir(parents=True, exist_ok=True)
VO_LEAD, TAIL = 0.6, 1.6
LT_IN, LT_OUT_BEFORE_END, LT_FADE = 0.8, 2.4, 0.4
OUTRO_SECONDS = 5
CRF = "23" if QUALITY == "review" else "18"
PRESET = "veryfast" if QUALITY == "review" else "slow"

lt_path = ROOT / "scenes" / "lower_thirds.json"
LOWER_THIRDS = json.loads(lt_path.read_text()).get(CUT, {}) if lt_path.exists() else {}


def run(cmd):
    subprocess.run(cmd, check=True)


parts = []
first = min(VO)
for sid in sorted(VO):
    s = VO[sid]
    if sid not in CLIPS:
        raise SystemExit(f"scene {sid} has VO but no clip in captures/{CUT}/clips.json")
    clip = CLIPS[sid]
    dur = round(VO_LEAD + s["duration"] + TAIL, 2)
    if clip["duration"] < dur - 0.05:
        print(f"warning: scene {sid} clip {clip['duration']}s shorter than {dur}s; last frame will be held", flush=True)
    out = WORK / f"scene_{sid}.mp4"
    lower = OVER / f"lower_{sid}.png"
    inputs = ["-i", clip["clip"], "-i", s["wav"]]
    fade_in = "fade=t=in:st=0:d=0.5" if sid == first else "null"
    vf = f"[0:v]tpad=stop_mode=clone:stop_duration=60,trim=duration={dur},setpts=PTS-STARTPTS,{fade_in}[v0]"
    if lower.exists() and sid in LOWER_THIRDS:
        inputs += ["-loop", "1", "-framerate", "30", "-i", str(lower)]  # loop the still: a one-frame input sits at t=0, before the fade-in, and never shows
        vf += (f";[2:v]format=rgba,fade=t=in:st={LT_IN}:d={LT_FADE}:alpha=1,"
               f"fade=t=out:st={dur - LT_OUT_BEFORE_END:.2f}:d={LT_FADE}:alpha=1[lt];"
               f"[v0][lt]overlay=x={LT_X}:y=H-h-64:shortest=0[v]")
    else:
        vf += ";[v0]null[v]"
    ms = int(VO_LEAD * 1000)
    af = f"[1:a]adelay={ms}|{ms},apad,atrim=duration={dur}[a]"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-t", str(dur), str(out)])
    parts.append(out)
    print(f"scene {sid}: {dur}s", flush=True)

outro_src = ROOT / "captures" / CUT / "outro.mp4"
if outro_src.exists():
    out = WORK / "scene_outro.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(outro_src), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
         "-vf", f"fade=t=out:st={OUTRO_SECONDS - 0.8}:d=0.8", "-t", str(OUTRO_SECONDS), "-c:v", "libx264", "-preset", PRESET,
         "-crf", CRF, "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)])
    parts.append(out)

lst = WORK / "concat.txt"
lst.write_text("".join(f"file '{p}'\n" for p in parts))
final = ROOT / "out" / f"{CUT}-{QUALITY}.mp4"
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(final)])
total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)],
                             capture_output=True, text=True).stdout.strip())
print(f"wrote {final} ({total:.1f}s, {total / 60:.1f} min)")
