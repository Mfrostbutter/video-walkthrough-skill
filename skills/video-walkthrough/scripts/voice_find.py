"""Find an ElevenLabs voice by name in the account and the shared library. Key from ELEVENLABS_KEY only."""
import os, sys, httpx
H = {"xi-api-key": os.environ["ELEVENLABS_KEY"]}
API = "https://api.elevenlabs.io/v1"
q = " ".join(sys.argv[1:])
r = httpx.get(f"{API}/voices", headers=H, timeout=30); r.raise_for_status()
for v in r.json()["voices"]:
    if q.lower() in v["name"].lower():
        print("account:", v["name"], v["voice_id"], v.get("category"), v.get("labels"))
r = httpx.get(f"{API}/shared-voices", headers=H, params={"search": q, "page_size": 10}, timeout=30); r.raise_for_status()
for v in r.json()["voices"]:
    print("shared:", v["name"], v["voice_id"], v.get("accent"), v.get("use_case"), v.get("descriptive"),
          "owner", v.get("public_owner_id"), "uses1y", v.get("usage_character_count_1y"), "free", v.get("free_users_allowed"))
