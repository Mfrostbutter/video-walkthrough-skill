#!/usr/bin/env bash
# Generate VO for one or more cuts. The ElevenLabs key reaches make_vo.py through the environment only; never printed.
#
#   ELEVENLABS_KEY=... scripts/run_vo.sh admin customer
#   KEY_CMD='<command that prints the key>' scripts/run_vo.sh admin      # e.g. a single-secret get from your secrets manager
#   ELEVENLABS_VOICE_ID=<id> ...                                         # default in make_vo.py is a premade voice
#
# PY: the Python with playwright + httpx (defaults to python3 on PATH).
set -euo pipefail
W="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-python3}"
K="${ELEVENLABS_KEY:-}"
if [ -z "$K" ] && [ -n "${KEY_CMD:-}" ]; then
  K="$(eval "$KEY_CMD")"
fi
[ -n "$K" ] || { echo "no ELEVENLABS_KEY in the environment and no KEY_CMD"; exit 1; }
echo "key length ${#K}"
[ $# -gt 0 ] || { echo "usage: run_vo.sh <cut> [<cut> ...]"; exit 1; }
for cut in "$@"; do
  echo "== $cut"
  VO_DIR="$W/vo/$cut" ELEVENLABS_KEY="$K" "$PY" "$W/scripts/make_vo.py" "${FORCE:+--force}"
done
