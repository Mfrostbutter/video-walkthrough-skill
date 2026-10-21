# Install and update

Choose one route per agent. The package is instructions plus scripts and card templates; it needs ffmpeg,
Python with Playwright and httpx, and an ElevenLabs key on the machine that runs it.

## Claude Code plugin

Inside a session:

```text
/plugin marketplace add Mfrostbutter/video-walkthrough-skill
/plugin install video-walkthrough@video-walkthrough-skill
```

Start a new session. The skill loads when a request matches its description, or call it with
`/video-walkthrough:video-walkthrough`. Update with `/plugin update video-walkthrough@video-walkthrough-skill`.

## Claude Code desktop app

1. In the prompt box, run `/plugin marketplace add Mfrostbutter/video-walkthrough-skill`.
2. Click **+** next to the prompt box, then **Plugins**, **Add plugin**, select **video-walkthrough** and pick
   a scope (user or project).
3. Start a new session.

No prompt for the plugin? Run `/plugin install video-walkthrough@video-walkthrough-skill` in the prompt box
instead. The app runs the scripts locally, so ffmpeg, Python with Playwright, and the ElevenLabs key must be
on this machine. The claude.ai chat app has no local execution and cannot run this skill.

## Clone and symlink

Stays in sync with `git pull`.

macOS and Linux:

```bash
git clone https://github.com/Mfrostbutter/video-walkthrough-skill.git
ln -s "$PWD/video-walkthrough-skill/skills/video-walkthrough" ~/.claude/skills/video-walkthrough
```

Windows (PowerShell, Developer Mode on or as admin):

```powershell
git clone https://github.com/Mfrostbutter/video-walkthrough-skill.git
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\video-walkthrough" -Target "$PWD\video-walkthrough-skill\skills\video-walkthrough"
```

## Copy the folder

Copy `skills/video-walkthrough/` whole into your agent's skills directory. `SKILL.md` alone does not work;
the scripts, scenes and references are what the skill runs.

| Agent | Personal skills directory |
| --- | --- |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.agents/skills/` |
| Project-scoped (Claude Code) | `<repo>/.claude/skills/` |

## Skills CLI

```sh
npx skills@latest add Mfrostbutter/video-walkthrough-skill --skill video-walkthrough
```

## Codex plugin

```sh
codex plugin marketplace add Mfrostbutter/video-walkthrough-skill
codex plugin add video-walkthrough@video-walkthrough-skill
```

## Machine prerequisites

```bash
brew install ffmpeg                       # or your package manager
python3 -m pip install playwright httpx
python3 -m playwright install chromium
```

The ElevenLabs key: `ELEVENLABS_KEY` in the environment, or `KEY_CMD='<command that prints it>'` for
`scripts/run_vo.sh`. The default voice is a public library voice; add it to your workspace once or set
`ELEVENLABS_VOICE_ID`. `scripts/voice_find.py <name>` finds a voice by name across the account and the
shared library.
