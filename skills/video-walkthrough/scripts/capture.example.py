"""Per-project scene file (example: an n8n instance with an admin and an editor persona). Copy to scripts/capture.py.

IN: CUT env (admin|customer), vo/<cut>/manifest.json, the subject's .env sourced (demo logins, API key), scenes/*.html.
OUT: captures/<cut>/scene_NN.mp4 and captures/<cut>/clips.json. Scene ids on argv limit the run.
Server state is reset per scene through the subject's API, so any scene can be re-shot alone.
"""
import json
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_lib import Capture, hide_cursor, open_page, start  # noqa: E402

BASE = os.environ.get("APP_BASE", "http://localhost:5678")
API = f"{BASE}/api/v1"
CUT = os.environ.get("CUT", "admin")
ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "captures" / "state.json"  # ids the scenes create (demo project, demo workflow)

HDR = {"X-N8N-API-KEY": os.environ["N8N_LAB_API_KEY"]}
PROJECT = json.loads(STATE.read_text())["project"] if STATE.exists() else None
CRED_NAME = "Policy: finance read-only"
WF_NAME = "Rates sync"

# First-run noise: hide survey overlays and banners; dismiss the personalisation modal by its button.
HIDE_CSS = (".el-overlay:has([data-test-id=nps-survey-modal]){display:none !important}"
            "[data-test-id=banner-stack]{display:none !important}")
DISMISS = ("button:has-text('Get started')", "[data-test-id=nps-survey-modal] .el-dialog__headerbtn")


# ---------- server state (off camera) ----------

def api():
    return httpx.Client(base_url=API, headers=HDR, timeout=30)


def state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(**kw):
    s = state(); s.update(kw); STATE.write_text(json.dumps(s, indent=2))


def find_credential(name: str):
    with api() as c:
        r = c.get("/credentials", params={"limit": 100}).json()
    return next((x for x in r.get("data", []) if x["name"] == name), None)


def ensure_credential(name: str) -> str:
    cred = find_credential(name)
    if cred:
        return cred["id"]
    with api() as c:
        r = c.post("/credentials", json={"name": name, "type": "guardedHttpPolicyApi",
                                          "data": {"policyName": "finance-readonly", "mode": "reference", "policyRef": "finance-readonly"}}).json()
        c.put(f"/credentials/{r['id']}/transfer", json={"destinationProjectId": PROJECT})
    return r["id"]


def recreate_workflow(with_credential: bool, method: str = "GET", url: str = "https://httpbin.org/get") -> str:
    """Fresh demo workflow in the demo project; old copies go through the API delete (archive)."""
    with api() as c:
        for wf in c.get("/workflows", params={"limit": 100, "name": WF_NAME}).json().get("data", []):
            if wf["name"] == WF_NAME:
                c.delete(f"/workflows/{wf['id']}")
        node = {"id": "n1", "name": "Fetch rates", "type": "CUSTOM.guardedHttpRequest", "typeVersion": 1,
                "position": [300, 0], "onError": "continueRegularOutput",
                "parameters": {"method": method, "url": url, "options": {"includePolicyInfo": True}}}
        if with_credential:
            node["credentials"] = {"guardedHttpPolicyApi": {"id": ensure_credential(CRED_NAME), "name": CRED_NAME}}
        body = {"name": WF_NAME, "nodes": [
            {"id": "t", "name": "When clicking 'Execute workflow'", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [0, 0], "parameters": {}},
            node],
            "connections": {"When clicking 'Execute workflow'": {"main": [[{"node": "Fetch rates", "type": "main", "index": 0}]]}},
            "settings": {"executionOrder": "v1"}}
        wf = c.post("/workflows", json=body).json()
        c.put(f"/workflows/{wf['id']}/transfer", json={"destinationProjectId": PROJECT})  # PUT into a team project 404s; create then transfer
    save_state(workflow=wf["id"])
    return wf["id"]


def reset_server_state(sid: str, kind: str):
    if kind == "create-cred":
        cred = find_credential(CRED_NAME)
        if cred:
            with api() as c:
                c.delete(f"/credentials/{cred['id']}")
        recreate_workflow(with_credential=False)
    elif kind in ("editor-get",):
        ensure_credential(CRED_NAME)
        recreate_workflow(with_credential=False, url="")
    elif kind in ("editor-post", "canvas"):
        ensure_credential(CRED_NAME)
        recreate_workflow(with_credential=True)


# ---------- login (off camera) ----------

def login_as(who: str):
    def login(page):
        page.goto(f"{BASE}/signin")
        page.wait_for_load_state("networkidle")
        page.fill("input[type=email], input[name=emailOrLdapLoginId]", os.environ[f"N8N_LAB_DEMO_{who}_EMAIL"])
        page.fill("input[type=password]", os.environ[f"N8N_LAB_DEMO_{who}_PASSWORD"])
        page.keyboard.press("Enter")
        page.wait_for_url(lambda u: "/signin" not in u, timeout=20000)
    return login


def open_as(page, who: str, url: str, settle: float, wait_for: str):
    open_page(page, login_as(who), url, settle=settle, wait_for=wait_for, dismiss_selectors=DISMISS)


# ---------- scenes ----------

NODE = "[data-test-id=canvas-node]:has-text('Fetch rates')"
OUTPUT = "[data-test-id=output-panel], [data-test-id=ndv-output-panel]"


def config_viewer(sc):
    """Card scene with timed highlights: scenes/code.html exposes hl(key) for rows tagged r-<key>."""
    p = sc.page
    p.goto((ROOT / "scenes" / "code.html").as_uri()); p.wait_for_timeout(500)
    hide_cursor(p)
    start(sc)
    sc.at(0.06); p.evaluate("hl('env')")
    sc.at(0.24); p.evaluate("hl('floor')")
    sc.at(0.50); p.evaluate("hl('finance')")
    sc.at(0.72); p.evaluate("hl('reload')")
    sc.at(0.86); p.evaluate("hl('require')")


def canvas(sc):
    p = sc.page
    open_as(p, "EDITOR", f"{BASE}/workflow/{state()['workflow']}", settle=3.0, wait_for=NODE)
    start(sc)
    sc.at(0.05); sc.glide_to(NODE, dx=40)
    sc.at(0.30); p.locator(NODE).first.dblclick()
    p.wait_for_timeout(1200)
    sc.at(0.45); sc.glide_to("[data-test-id=node-credentials-select]", dx=120)
    sc.at(0.62); sc.glide_to("[data-test-id=parameter-input-method]", dx=120)
    sc.at(0.78); sc.glide_to("[data-test-id=parameter-input-url]", dx=120)


def create_cred(sc):
    p = sc.page
    open_as(p, "ADMIN", f"{BASE}/projects/{PROJECT}/credentials", settle=2.5, wait_for="[data-test-id=add-resource-credential]")
    start(sc)
    sc.at(0.10); sc.click("[data-test-id=add-resource-credential]")
    p.wait_for_timeout(900)
    sc.at(0.20); p.keyboard.type("Guarded", delay=70); p.wait_for_timeout(900); p.keyboard.press("Enter"); p.wait_for_timeout(600)
    try:
        p.locator("[data-test-id=new-credential-type-button]").click(timeout=3000)
    except Exception:
        pass
    p.wait_for_timeout(1500)
    sc.at(0.36); sc.click("[data-test-id=credential-name]", dx=60)
    p.keyboard.press("Meta+A"); p.keyboard.type(CRED_NAME, delay=55); p.keyboard.press("Enter")
    sc.at(0.50); sc.type("[data-test-id=parameter-input-policyName] input", "finance-readonly")
    sc.at(0.68); sc.type("[data-test-id=parameter-input-policyRef] input", "finance-readonly")
    sc.at(0.80); sc.click("[data-test-id=credential-save-button]")
    p.wait_for_timeout(1200)
    sc.at(0.90); sc.glide_to("[data-test-id=credential-connection-parameter]", dx=200)


def editor_get(sc):
    p = sc.page
    open_as(p, "EDITOR", f"{BASE}/workflow/{state()['workflow']}", settle=3.0, wait_for=NODE)
    start(sc)
    sc.at(0.08); p.locator(NODE).first.dblclick()
    p.wait_for_timeout(1200)
    sc.at(0.22); sc.click("[data-test-id=node-credentials-select]", dx=120)
    p.wait_for_timeout(800)
    sc.at(0.32); sc.click(f".el-select-dropdown__item:has-text('{CRED_NAME}'), li:has-text('{CRED_NAME}')", dx=60)
    p.wait_for_timeout(600)
    sc.at(0.52); sc.click("[data-test-id=parameter-input-url] input, [data-test-id=parameter-input-url] [contenteditable]", dx=80)
    p.keyboard.type("https://httpbin.org/get", delay=45)
    sc.at(0.70); sc.click("[data-test-id=node-execute-button]")
    p.wait_for_timeout(2500)
    sc.at(0.84); sc.glide_to(OUTPUT, dx=300, dy=320)


def editor_post(sc):
    p = sc.page
    open_as(p, "EDITOR", f"{BASE}/workflow/{state()['workflow']}", settle=3.0, wait_for=NODE)
    start(sc)
    sc.at(0.04); p.locator(NODE).first.dblclick()
    p.wait_for_timeout(1200)
    sc.at(0.14); sc.click("[data-test-id=parameter-input-method]", dx=120)
    p.wait_for_timeout(700)
    sc.at(0.22); sc.click(".el-select-dropdown__item:has-text('POST'), li:has-text('POST')", dx=40)
    p.wait_for_timeout(500)
    sc.at(0.32); sc.click("[data-test-id=node-execute-button]")
    p.wait_for_timeout(2500)
    sc.at(0.48); sc.glide_to(OUTPUT, dx=300, dy=320)
    sc.at(0.80); sc.glide_to(OUTPUT, dx=300, dy=420)


cap = Capture(ROOT, CUT, hide_css=HIDE_CSS, reset=reset_server_state)

if CUT == "admin":
    SCENES = [("01", "card", cap.card("title")), ("02", "canvas", canvas), ("03", "card", config_viewer),
              ("04", "create-cred", create_cred), ("05", "editor-get", editor_get), ("06", "editor-post", editor_post),
              ("07", "card", cap.card("closing"))]
else:
    SCENES = [("01", "card", cap.card("title")), ("02", "canvas", canvas), ("03", "editor-get", editor_get),
              ("04", "editor-post", editor_post), ("05", "card", cap.card("closing"))]

if __name__ == "__main__":
    if not PROJECT:
        sys.exit("captures/state.json needs {'project': <demo project id>}")
    cap.run(SCENES, only=set(sys.argv[1:]))
