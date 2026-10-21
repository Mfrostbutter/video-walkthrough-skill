# Video walkthrough skill

**Narrated walkthrough videos of a running web app, produced end to end by your coding agent.**

Give the agent a running app (an n8n instance, an internal tool, a prototype), an audience and a target
length. It writes a per-scene voice script, generates the voiceover with ElevenLabs, films each scene with
Playwright paced to the narration, renders title, lower-third, code and closing cards from HTML, and cuts the
whole thing with ffmpeg. Output: a 1080p MP4 with voice, captions and an outro. No screen recorder, no
editor, no GUI. Re-cuts and re-shoots of one scene are a single command.

Built for [Claude Code](https://claude.com/claude-code) and any agent that supports
[Agent Skills](https://agentskills.io/home). MIT licensed.

## What you get

- **A voice script written for the audience.** One section per scene, read-aloud prose, a 14 characters per
  second budget so a 3:00 cut is about 2,700 characters.
- **Voiceover first.** ElevenLabs generates one clip per scene and a manifest with durations. Every later
  stage reads those durations, so a regenerated line never breaks the pacing. Reruns regenerate only the
  sections whose text changed.
- **Scripted captures.** One Playwright context per scene, login and navigation off camera, a fake cursor,
  actions paced to the narration with `sc.at(frac)`, server state reset before every scene so any scene
  can be re-shot alone.
- **Cards from HTML.** Title, closing, outro, lower thirds and a code card with row highlighting, all 1920x1080
  pages with CSS animation, rendered by Playwright. Tokens live in one `brand.css`.
- **ffmpeg assembly.** Per-scene mux with the voice, lower-third fades, concat, silent outro. A review render in
  about a minute, a final render at crf 18.
- **Frame-grid review at every stage.** Four frames per clip before assembly, six from the cut before the
  final, so a wrong page, a stray cursor or a failed save is caught before anyone watches it.
- **Two cuts from one shoot.** A customer overview and an admin cut share captures and cards and keep their
  own scripts, voice and overlays.
- **n8n notes.** Selectors, first-run modals, canvas framing, public API calls for seeding state, and the
  traps met filming n8n 2.3x, in `references/n8n-capture-notes.md`.

## Install

Claude Code, inside a session:

```text
/plugin marketplace add Mfrostbutter/video-walkthrough-skill
/plugin install video-walkthrough@video-walkthrough-skill
```

Or clone and symlink the skill folder:

```bash
git clone https://github.com/Mfrostbutter/video-walkthrough-skill.git
ln -s "$PWD/video-walkthrough-skill/skills/video-walkthrough" ~/.claude/skills/video-walkthrough
```

Or copy `skills/video-walkthrough/` into your agent's skills directory. Keep `references/`, `scenes/` and
`scripts/`; `SKILL.md` alone is not enough. Other routes are in [docs/installation.md](docs/installation.md).

## Requirements

- `ffmpeg` and `ffprobe` on PATH.
- Python 3.11 or newer with `playwright` and `httpx`, then `python -m playwright install chromium`.
- An ElevenLabs API key, reachable as `ELEVENLABS_KEY` in the environment or through a one-line
  `KEY_CMD` that prints it from your secrets manager. The key is never written to a file.
- The app you are filming, running and seeded with data you are allowed to show.

## Use it

Start a new session and ask:

> Make a three minute admin walkthrough of the app at http://localhost:5678. Audience is the customer's
> platform team.

The skill asks four shaping questions in one batch (voice, audience and length, assembly, output folder),
surveys the app, writes the script, and runs the pipeline:

```
vo/<cut>/script.md -> scripts/make_vo.py       ElevenLabs -> vo/<cut>/NN.wav + manifest.json
scenes/*.html + lower_thirds.json               cards and lower thirds (HTML, brand tokens)
scripts/capture.py (uses capture_lib.py)        Playwright -> captures/<cut>/scene_NN.mp4 + clips.json
scripts/render_overlays.py                      -> overlays/<cut>/lower_NN.png, captures/<cut>/outro.mp4
scripts/frames.py                               -> review/<cut>/scene_NN.png
scripts/assemble_ffmpeg.py                      -> out/<cut>-review.mp4, then out/<cut>-final.mp4
```

Work happens in a scratch folder outside any synced repo; finished files are copied to the folder you name.

## Repository layout

| Path | Contents |
|---|---|
| `skills/video-walkthrough/SKILL.md` | the skill: preflight, shaping questions, script rules, capture, assembly, delivery, guardrails |
| `skills/video-walkthrough/scripts/` | `make_vo.py`, `run_vo.sh`, `voice_find.py`, `capture_lib.py`, `capture.example.py`, `render_overlays.py`, `frames.py`, `assemble_ffmpeg.py`, an example voice script |
| `skills/video-walkthrough/scenes/` | `brand.css`, `title.html`, `closing.html`, `outro.html`, `lower.html`, `code.html`, `lower_thirds.json` |
| `skills/video-walkthrough/references/` | capture and voice numbers, the ffmpeg filter graph, n8n-specific notes |
| `docs/installation.md` | every install route |

## Guardrails the skill enforces

- No secrets in any file it writes. Keys travel from the environment to the process only.
- Voiceover before capture. The voice decides each scene's length.
- Invented data only on camera, labelled as such; no customer data.
- An identifier scan of every filmed route (hostnames, LAN addresses, names) before recording.
- Runtime verification of whatever the video claims, through the app's API, not a green toast.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and pull requests welcome; keep examples synthetic.

## License

[MIT](LICENSE) © Michael Frostbutter
