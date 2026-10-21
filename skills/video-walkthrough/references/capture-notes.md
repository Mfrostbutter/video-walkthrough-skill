# Capture and voice: details and measured numbers

## Playwright capture

- Python Playwright, `pw.chromium.launch(headless=True)`; `python -m playwright install chromium`.
- `new_context(viewport=1920x1080, device_scale_factor=1, record_video_dir=RAW, record_video_size=1920x1080,
  color_scheme="dark")`. One context per scene.
- `ctx.add_init_script(init_js(...))` seeds `PRESEED` into localStorage (first-run tours off), applies
  `HIDE_CSS`, and injects the pointer: a `position:fixed` div with a 22 px SVG arrow, `z-index` max, updated
  on `mousemove` (capture phase), scaled to 0.8 on `mousedown`. It runs on every navigation in the context.
- Timing that reads well at 30 fps: glide 28 steps, type delay 45 to 60 ms, 500 to 1,500 ms pauses after a
  click that opens a panel, 2.5 s after an execute button before gliding to the output.
- `page.video.path()` is final only after `ctx.close()`; capture the `page.video` object before closing, then
  rename. Convert with `-ss <trim> -r 30 -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -an`.
- `start(sc)` is the on-camera mark. Everything before it (login, navigation, modal dismissal) is cut by `-ss`.
  A scene therefore opens on the page the voice is about, with no visible setup.
- Modals: dismiss by clicking the app's own button. Posting to the app's API from the page context without the
  headers the app expects can return 401 and drop the session (n8n's survey endpoint does).
- When the app auto-selects the only available option (n8n picks the sole credential), the "editor picks it"
  beat still clicks the dropdown but reads as pre-filled; a decoy option makes the pick visible.

## Identifier hygiene

Before filming, open each route in Playwright, `wait_for_load_state("networkidle")`, and grep `page.content()`
for hostnames, LAN IPs, surnames, repo names, customer names. Headless recording shows no URL bar.

## Login and sessions

- Demo credentials come from `.env` or a secrets manager into environment variables; the capture script reads
  `os.environ`, never a literal. Two personas (admin, editor) need two accounts.
- Login per scene off camera is simplest and is what `open_page` does. `storage_state` reuse is an option when
  login is slow; delete the state file at close-out, it holds a session cookie.

## VO before capture

`make_vo.py` runs before `capture.py`. The capture script reads `vo/<cut>/manifest.json` and refuses a scene
that has no VO entry; `hold_min()` keeps each clip to VO + tail.

## Pacing a scene to its voice

`Scene.at(frac)` waits until `VO_LEAD + frac * vo_seconds` since `start()`. Each on-screen action starts within
about a second of the words that name it; descriptive stretches hold on the element being described; the final
action fires as the last sentence lands. Typical shape for a form scene: open the dialog at 0.10, pick a type at
0.20, name at 0.36, first field at 0.50, second field at 0.68, save at 0.80, settle on the result at 0.90.
Verify with the frame grids before assembling.

## ElevenLabs

- Discover: `GET /v1/voices` (name, voice_id, category premade|professional), `GET /v1/models`,
  `GET /v1/user/subscription`. The voice the user names may not be on the account; pick a premade substitute,
  say so, and record the id in the manifest (`make_vo.py` does).
- `POST /v1/text-to-speech/{voice_id}?output_format=mp3_44100_128`, `eleven_v3`, settings
  stability 0.5, similarity 0.8, style 0.12, speaker boost, speed 1.0. Default voice: Jessica Anne Bogart,
  VO Professional (`lxYfHSkYm1EzQzGhdbfc`, library voice; add it to a new workspace with
  `POST /v1/voices/add/{public_owner_id}/{voice_id}` first). Matilda on multilingual_v2 at 1.08 read robotic
  (customer shoot, 2026-10-19); speed above 1.0 flattens prosody.
- Voice scouting: `GET /v1/shared-voices?gender=female&language=en&sort=usage_character_count_1y` ranks the
  library by real use; every row carries a `preview_url` to audition without adding the voice. Accept only `audio/*` bodies with ID3
  or MPEG sync bytes; retry otherwise.
- Loudness: `loudnorm=I=-16:TP=-1.5:LRA=11`, 48 kHz mono WAV.
- Measured: 14.0 characters per second for the default voice at speed 1.0 (three cuts, 2026-10-19);
  16.4 at speed 1.08 with Matilda. Budget 14 per target second.
- The script hash per scene lives in the manifest; a one-line edit regenerates one scene.

## Two cuts from one shoot

Keep `scenes/` and `scripts/` shared; `vo/<cut>/`, `captures/<cut>/`, `overlays/<cut>/`, `review/<cut>/` per
cut. The customer cut reuses the admin cut's scene functions with its own scene list and script; a combined
scene (create, save, then the sharing tab in one take) keeps a short cut moving.
