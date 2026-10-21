# Scripts

Copy `scripts/` and `scenes/` into `<workdir>/<slug>/`, rename `capture.example.py` to `capture.py`, then edit the
constants at the top of each file. Each script states IN / OUT at the top. Order:
`run_vo.sh` -> `render_overlays.py` -> `capture.py` -> `frames.py` -> `assemble_ffmpeg.py` (review) -> look ->
`assemble_ffmpeg.py` (final).

| File | Stage | Edit before use |
|---|---|---|
| `script.example.md` | voice script format the VO generator parses | all prose; keep the `## NN Title (…)` headings; one copy per cut at `vo/<cut>/script.md` |
| `make_vo.py` | ElevenLabs TTS per scene, hash-skipped reruns | `MODEL`, `SETTINGS`; voice via `ELEVENLABS_VOICE_ID`, key via `ELEVENLABS_KEY` |
| `run_vo.sh` | runs `make_vo.py` per cut with the key from the environment or `KEY_CMD` | `PY` if the default python lacks httpx |
| `capture_lib.py` | shared recorder: `Capture`, `Scene.at(frac)`, `open_page`, `start`, cards, webm to mp4, `clips.json` | nothing, usually |
| `capture.example.py` | per-project scenes, login, server-state reset through the subject's API | `BASE`, env var names, selectors, the scene list per cut |
| `render_overlays.py` | lower-third PNGs with alpha and the silent outro clip, per cut | nothing; text lives in `scenes/lower_thirds.json` |
| `frames.py` | review grids per clip; `FINAL=1` for six frames of the assembled cut | nothing |
| `assemble_ffmpeg.py` | per-scene mux, lower-third fades, concat, outro; `QUALITY=review` or `final` | `VO_LEAD`, `TAIL`, lower-third position if the app's UI has content bottom-left |

Environment: `CUT=<cut>` on every per-cut script (default `main`). The subject's `.env` is sourced by absolute path
before `capture.py` (`set -a; source /abs/path/.env; set +a`) so demo logins and API keys arrive as environment
variables and never sit in a script. Python deps: `playwright`, `httpx`; `python -m playwright install chromium`.
ffmpeg and ffprobe on PATH.
