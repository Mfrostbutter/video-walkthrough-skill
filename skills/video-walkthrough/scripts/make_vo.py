"""Generate one voiceover clip per scene from <VO_DIR>/script.md with ElevenLabs.

IN: ELEVENLABS_KEY in the environment (never written anywhere), VO_DIR (default vo/), ELEVENLABS_VOICE_ID (optional).
OUT: <VO_DIR>/NN.mp3, <VO_DIR>/NN-<hash>-s<speed>.wav (48 kHz mono, loudness-normalised), <VO_DIR>/manifest.json.
Idempotent: a scene whose text hash matches the manifest is skipped unless --force.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
VO = Path(os.environ.get("VO_DIR", HERE.parent / "vo"))
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "lxYfHSkYm1EzQzGhdbfc")  # Jessica Anne Bogart, VO Professional (library voice)
MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_v3")
SETTINGS = {"stability": 0.5, "similarity_boost": 0.8, "style": 0.12, "use_speaker_boost": True,
            "speed": float(os.environ.get("ELEVENLABS_SPEED", "1.0"))}


def parse_script(md: str) -> list[dict]:
    """Sections '## NN Title (page note)' -> scenes; text after a '---' preamble, before 'Notes for the edit:'."""
    body = md.split("\n---\n")[1] if "\n---\n" in md else md
    body = body.split("\nNotes for the edit:")[0]
    scenes = []
    for m in re.finditer(r"^## (\d\d) (.+?)(?: \(.*?\))?\s*$\n(.*?)(?=^## |\Z)", body, re.S | re.M):
        text = " ".join(line.strip() for line in m.group(3).strip().splitlines() if line.strip())
        scenes.append({"id": m.group(1), "title": m.group(2).strip(), "text": text})
    return scenes


def tts(client: httpx.Client, key: str, text: str, out: Path) -> None:
    """One scene. Retries on 5xx/429 and on a body that is not audio; never leaves a partial file."""
    last = ""
    for attempt in range(4):
        try:
            r = client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
                params={"output_format": "mp3_44100_128"},
                headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
                json={"text": text, "model_id": MODEL, "voice_settings": SETTINGS},
                timeout=180,
            )
        except httpx.HTTPError as exc:
            last = f"transport: {exc}"
        else:
            ctype = r.headers.get("content-type", "")
            is_audio = r.status_code == 200 and ctype.startswith("audio/") and len(r.content) > 2000 \
                and (r.content.startswith(b"ID3") or r.content[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"))
            if is_audio:
                tmp = out.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.replace(out)
                return
            last = f"{r.status_code} {ctype} {len(r.content)}B {r.text[:200] if not ctype.startswith('audio/') else ''}"
            if r.status_code in (400, 401, 403, 422):
                break
        wait = 3 * (attempt + 1)
        print(f"   tts attempt {attempt + 1} failed ({last}); retry in {wait}s", flush=True)
        time.sleep(wait)
    sys.exit(f"TTS failed for {out.name}: {last}")


def to_wav(mp3: Path, tag: str) -> Path:
    # content-addressed name: a regenerated take never overwrites a wav an assembly still references
    wav = mp3.with_name(f"{mp3.stem}-{tag}.wav")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(mp3),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "1", str(wav)], check=True)
    return wav


def duration(path: Path) -> float:
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def main() -> None:
    key = os.environ.get("ELEVENLABS_KEY", "")
    if len(key) < 20:
        sys.exit("ELEVENLABS_KEY missing from the environment")
    force = "--force" in sys.argv
    scenes = parse_script((VO / "script.md").read_text(encoding="utf-8"))
    if not scenes:
        sys.exit(f"no scenes parsed from {VO / 'script.md'}")
    manifest_path = VO / "manifest.json"
    old = {s["id"]: s for s in json.loads(manifest_path.read_text())["scenes"]} if manifest_path.exists() else {}
    total_chars = 0
    with httpx.Client() as client:
        for s in scenes:
            mp3 = VO / f"{s['id']}.mp3"
            digest = hashlib.sha256(s["text"].encode("utf-8")).hexdigest()[:12]
            if mp3.exists() and not force and old.get(s["id"], {}).get("sha") == digest:
                s.update(old[s["id"]])
                print(f"{s['id']} unchanged ({s['duration']}s)", flush=True)
                continue
            print(f"{s['id']} {s['title']}: {len(s['text'])} chars", flush=True)
            total_chars += len(s["text"])
            tts(client, key, s["text"], mp3)
            wav = to_wav(mp3, digest[:8] + ("-s%d" % int(SETTINGS["speed"] * 100)))
            s.update({"mp3": str(mp3), "wav": str(wav), "duration": round(duration(wav), 2), "sha": digest})
            print(f"   -> {wav.name} {s['duration']}s", flush=True)
    total = round(sum(s["duration"] for s in scenes), 1)
    manifest_path.write_text(json.dumps({"voice_id": VOICE_ID, "model": MODEL, "total_seconds": total,
                                         "scenes": scenes}, indent=2), encoding="utf-8")
    print(f"generated {total_chars} chars; total VO {total}s ({total / 60:.1f} min); wrote {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
