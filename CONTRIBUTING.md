# Contribute

Open an [issue](https://github.com/Mfrostbutter/video-walkthrough-skill/issues/new?template=feedback.yml)
for an install problem, a capture that misbehaves, a trap worth recording, or a selector that moved in a new
app version. State the agent and version, the app and version, what you expected and what happened. Use
synthetic examples. Never include customer data, session cookies, API keys or recordings of real accounts.

## Change the repository

1. Branch for one clear change.
2. Edit `skills/video-walkthrough/`. Keep `SKILL.md` imperative and under about 300 lines; push long or
   app-specific detail into `references/`.
3. Run the checks: `python3 -m py_compile skills/video-walkthrough/scripts/*.py` and
   `python3 -c "import json,sys;[json.load(open(p)) for p in sys.argv[1:]]" .claude-plugin/*.json .codex-plugin/*.json skills/video-walkthrough/scenes/*.json`.
4. Open a pull request with a conventional title, such as `fix: wait for the NDV before typing`.

A good addition states a measured number (characters per second, a zoom factor, a timeout that held) or a
trap met on a real shoot, with the app version it was seen on. Guesses go in an issue, not the skill.

Script improvements made during a shoot belong here, not only in the project's scratch folder.

Changes use the repository's [MIT license](LICENSE).
