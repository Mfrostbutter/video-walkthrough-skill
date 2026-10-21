---
name: video-walkthrough
description: >-
  Produce a narrated walkthrough video of a running web app from one machine with no After Effects:
  scripted Playwright screen captures (one clip per scene, fake cursor, 1080p), an ElevenLabs voiceover
  from a per-scene script, HTML title, lower-third, code and outro cards rendered by Playwright, and the
  whole cut assembled by ffmpeg (per-scene mux with the VO, lower-third fades, concat, review and final
  quality). Use whenever the user asks for a walkthrough, demo, explainer, product tour, screencast, or
  "make a video of the app" for a localhost or hosted web UI and After Effects is absent, closed, on
  another machine, or not wanted. Also use to re-cut an existing walkthrough (new audience, new VO,
  inserted scenes, different length), to produce two cuts from one set of captures, or to film one page
  for a social clip.
license: MIT
metadata:
  version: "1.0.0"
---

# Video walkthrough, ffmpeg edition

A deterministic pipeline, not a screen-recorder session. Every stage writes files the next stage reads, so
any stage reruns alone and the edit never depends on a human timing anything by hand. Python Playwright
records (the Playwright MCP cannot record video), ElevenLabs speaks, Playwright renders the cards from
HTML, ffmpeg cuts. Nothing in the chain needs a GUI. Keep a short worklog at `_worklogs/YYYY-MM-DD-<slug>/WORKLOG.md` from step 0
and append an entry whenever a tool surprises you; it is the record a re-cut or a re-shoot starts from.

```
vo/<cut>/script.md -> scripts/make_vo.py       ElevenLabs -> vo/<cut>/NN.wav + manifest.json   (VO FIRST)
scenes/*.html + lower_thirds.json               cards, lower thirds, outro (HTML, brand tokens)
scripts/capture.py (uses capture_lib.py)        Playwright -> captures/<cut>/scene_NN.mp4 + clips.json
scripts/render_overlays.py                      -> overlays/<cut>/lower_NN.png, captures/<cut>/outro.mp4
scripts/frames.py                               -> review/<cut>/scene_NN.png  (look before you assemble)
scripts/assemble_ffmpeg.py                      -> out/<cut>-review.mp4, then out/<cut>-final.mp4
```

Working directory: `<workdir>/<slug>/` with `vo/ scenes/ captures/ overlays/ review/ out/ scripts/ _worklogs/`.
`<workdir>` is a scratch folder outside any synced repo (`~/video-work/` works); raw webm and renders are
hundreds of MB and the folder is disposable. Several cuts (an admin cut and a customer cut, say) share
`scenes/` and `scripts/` and keep their own `vo/<cut>/`, `captures/<cut>/`, `overlays/<cut>/`. The durable
copy of the scripts is this skill's `scripts/`; copy improvements back here before closing out.

## 0. Preflight

One pass, before writing anything:

- **ffmpeg and ffprobe** on PATH (`brew install ffmpeg`, with the user's OK). A Python env with `playwright`
  and `httpx`, and `python -m playwright install chromium`. No editor app, no GUI, no scripting pref.
- **TTS key** reachable: fetch it from the secrets manager into a shell variable inside a helper script
  (`scripts/run_vo.sh`), print only its length, then `GET /v1/voices`. Default voice: Jessica Anne Bogart,
  VO Professional (`lxYfHSkYm1EzQzGhdbfc`) on `eleven_v3` at speed 1.0; it must exist in the workspace
  (`POST /v1/voices/add/...` once). The voice the user names may not be on the account; list the voices
  and pick a substitute, and say so in the handoff.
- **Subject app** running and current. Rebuild a local playground from source before filming.
- **Data.** Count rows behind every page you intend to film. Empty pages need seeding (the app's API, its
  fixtures, or a synthetic run). Invented data only on camera.
- **Identifier scan.** For a SPA, open each route in Playwright and grep `page.content()` for hostnames,
  LAN IPs, personal names, repo names. Headless capture has no URL bar, so localhost never shows.
- **Login.** Demo accounts whose credentials live in `.env` or a secrets manager, read through `os.environ`,
  never typed into the script. Admin and editor personas need two accounts.
- **Brand.** If a brand skill exists for the subject (tokens, fonts, logo), load it and take every colour and
  font from it into `scenes/brand.css`. One mode per surface.

## 1. Ask the shaping questions in one batch

Recommended option first on each. Nothing downstream starts before the answers land.

1. Voice: the default (Jessica Anne Bogart, VO Professional), the user's own ElevenLabs clone, or another
   library voice (offer the `shared-voices` usage ranking and its previews).
2. Audience and technical level, plus length. Offer the cuts plainly: a customer or CSM overview (what it is,
   what you do, what you get) and an admin or engineering cut (how to set it up). "Both" is a normal answer;
   the captures are shared and only the scripts differ.
3. Assembly: finish on this machine with ffmpeg (default) or hand the captures and VO to a machine with an
   editor. Ask only if the user raised the editor question.
4. Output location for the finished files (a Desktop folder beats a nested work tree).

## 2. Survey, then populate

One screenshot per route with the first-run modals dismissed, before the script is written. Note the
`data-test-id` or stable selectors you will drive. Seed data through the app's own API so every filmed page
has content; keep the seeding in the capture script's `reset_server_state()` so a scene can be re-shot in
isolation (delete and recreate the demo record, transfer it to the demo project, and so on).

## 3. Write the voice script to the audience, then generate VO

`vo/<cut>/script.md`: one `## NN Title (page)` section per scene, prose only, read-aloud voice. Section 01
narrates the title card; the last narrated section is the closing card; the outro card after it is silent.
The VO generator parses the headings, so the heading shape is load-bearing. Lower-third captions live in
`scenes/lower_thirds.json`, keyed by cut and scene id.

Budget 14 characters per target second (measured 14.0 chars/s with the default voice at speed 1.0). A 3:00 admin cut is about
2,700 characters; a 1:45 overview about 1,600. Spell out things the voice would mangle (`NODES underscore
EXCLUDE`). Plain spoken English, short sentences, one idea per scene, product names said plainly. No
analogies, no "in this video", no contrast phrasing in an overview cut.

Run `scripts/run_vo.sh <cut> [<cut>]`. It writes `vo/<cut>/manifest.json` with per-scene durations, which
the capture and assembly steps read. A rerun regenerates only sections whose text changed (hash skip).

## 4. Build the cards

`scenes/brand.css` holds the tokens and `@font-face` lines; `title.html`, `closing.html`, `outro.html`,
`lower.html` and `code.html` use them. Cards are 1920x1080 pages that animate with CSS on load (`.fade`,
`.d1..d3`), so a card scene is just `page.goto(file://...)` held for the VO. `code.html` shows a config or
code file with `hl('<key>')` highlighting rows tagged `r-<key>` and scrolling them into view; the scene
calls `hl()` at beat fractions. `lower.html` takes `?text=` and `?kicker=` and is screenshotted with
`omit_background=True` for an alpha PNG. `render_overlays.py` renders every lower third in
`lower_thirds.json` and a 5 s silent outro clip per cut. Check the outro text fits the frame at the font
sizes used before recording anything.

## 5. Capture with Playwright, one context per scene

`scripts/capture_lib.py` is the library; `scripts/capture.example.py` is the per-project file you copy to
`scripts/capture.py` and edit. Keep these properties:

- **Login and navigation happen off camera.** A scene opens on the page the voice is about:
  `open_page()` logs in, waits for `networkidle`, then navigates and waits for the page's anchor element with
  retries (a `goto` right after login races the app's post-login redirect). Then `start(sc)` marks the
  on-camera start and `to_mp4` trims everything before it.
- **One browser context per scene**, closed before the next, so each scene is its own webm. A fresh
  context resets the browser, not the server; `reset_server_state(sid)` runs first in every scene.
- **Pace every action to the narration** with `sc.at(frac)`: a fraction of the scene's VO duration, read
  from the manifest, so a regenerated line does not break the pacing. Each on-screen action starts within a
  second of the words that name it; descriptive stretches hold on the element described; the final action
  fires as the last sentence lands. The action must never finish before the voice does. `hold_min()` keeps
  the clip to VO + tail.
- **Fake cursor** injected by the init script; **hide it on card scenes** (`hide_cursor`). Dismiss first-run
  modals by clicking their button, not by posting to the app's API (an unauthenticated call can drop the
  session). Hide survey overlays and banners with `HIDE_CSS`; pre-seed `localStorage` with `PRESEED`.
- Selectors: prefer `data-test-id` and row classes with `:has-text()`; keep `glide_to` and `click` tolerant
  (log and skip when absent, never wait out a timeout on camera).
- **Patching the script during a run does nothing for that run.** Finish edits, then start.
- `clips.json` is merged after every scene, so re-shooting one scene is `python scripts/capture.py 07`.

Then `frames.py`: four frames per clip at 10/40/70/95 percent of the VO in a 2x2 grid. Look at every grid.
Thirty seconds of looking catches a wrong page, a stray cursor, a scene that ran ahead of its voice, or a
save that failed with a toast in the corner.

## 6. Assemble with ffmpeg

`assemble_ffmpeg.py` per scene: pad the clip's last frame (`tpad`), trim to `VO_LEAD + vo + TAIL`, fade the
first scene in, overlay the lower third PNG with alpha fades (in at 0.8 s, out 2 s before the end), delay the
WAV by `VO_LEAD`, pad and trim the audio, encode h264 + AAC at 30 fps. Then concat the parts and the silent
outro with `-c copy` and `+faststart`. `QUALITY=review` (crf 23, veryfast) renders in about a minute for a
4-minute cut; `QUALITY=final` (crf 18, slow) in a few. Different filenames, so a player holding the review
file never blocks the final.

Review: pull six frames from the assembled cut (title, a lower third, two mid-scene, closing, outro) into
one `xstack` grid, `ffprobe` the streams, and check the VO lead with `silencedetect` on one scene. Then
render the final. Details and the filter graph are in `references/ffmpeg-assembly.md`.

**Inserting a scene** (the usual "also cover X"): keep the closing card last, renumber it by renaming its
files (`vo/<cut>/NN.mp3`, the content-addressed wav, the manifest id, `captures/<cut>/scene_NN.mp4`, the
`clips.json` key) rather than regenerating, add the new section and lower third, generate VO (only the new
section is billed), capture the one scene, re-assemble. Order of scenes is the sorted manifest.

## 7. Deliver and close out

- Copy the finals under their delivery names plus the written instructions into the location the user named.
  Report length, resolution, the voice actually used, and anything substituted.
- Keep: `out/*-final.mp4`, `vo/`, `captures/*.mp4`, `scenes/`, `scripts/`, the worklog. Raw webm can go.
- Verify at runtime whatever the video claims (a saved setting, a blocked request) through the app's API,
  and say which run proved it. A green toast on camera is a claim; the API response is the proof.
- Copy script improvements back into this skill. Note subject artifacts left behind (demo users, projects).

## Guardrails

- **No secrets in any file you write.** TTS keys travel shell variable to process only; print a length.
  Demo logins come from `.env` or a secrets manager. Values an identity script creates go straight into the
  subject's `.env`, never into the transcript.
- **VO before capture.** The voice decides each scene's length; capturing first means guessing and
  freezing frames.
- **Look at frames at every stage.** Clip grids before assembly, cut frames before the final. A failed save,
  a stale card, an "[undefined]" preview and a cursor parked on the text were all caught this way.
- **One context per scene, server state reset per scene, login off camera.** Three rules that make a
  re-shoot of scene 7 identical to the first shoot.
- **Every stage stops the chain.** `set -o pipefail`; never `step | tail || exit`.
- **Do not put anything in a synced repo tree.** Work in `<workdir>`, deliver by copy.
- **Invented data only on camera**, labelled as such wherever the app supports it, no customer data ever.
