# Security

The skill drives a browser against the app you point it at and sends voice-script text to ElevenLabs.
Review the script before it is spoken and the frame grids before a cut leaves the machine.

## What the skill touches

- The ElevenLabs key is read from the environment (`ELEVENLABS_KEY` or the output of `KEY_CMD`) and
  passed to one process. It is never written to a file. The scripts print its length, not its value.
- Demo logins come from the subject app's `.env` or a secrets manager into environment variables.
  Nothing in `scripts/` holds a literal credential.
- Playwright `storage_state` files hold a session cookie. Delete them at close-out.
- Recordings show whatever the page shows. Run the identifier scan in the skill's preflight and film
  invented data only.

## Report a vulnerability

Open a private security advisory on this repository or email the maintainer. Include the affected version,
the impact and steps that reproduce it with synthetic data. Do not put credentials or recordings in a
public issue.
