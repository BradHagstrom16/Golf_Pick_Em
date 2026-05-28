"""Authenticated impeccable-detect render harness (ephemeral critique tooling).

`impeccable detect` has no auth flag, so its anonymous Puppeteer hits the
`@login_required`/`@admin_required` redirect and measures index.html instead of
the gated template. This harness renders each gated template through Flask's test
client with an admin session injected (`sess['_user_id']='1'`), writes the rendered
HTML (which links the real `/static/css/style.css`) to a repo-root file under
`.critique_shots/`, serves the repo root, and runs `impeccable detect --json` against
the URL — so Puppeteer renders the real gated DOM + real style.css with no auth.

Non-mutating: GET + the non-saving `load_field` POST only.

Usage:
    python .critique_shots/harness.py            # render + detect all PAGES, print post-filter counts
    python .critique_shots/harness.py --render    # render HTML files only (no detect)

Requires the real dev DB (golf_pickem.db) — do NOT set FLASK_ENV=testing.
"""
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

# Render against the real seeded dev DB, never the in-memory testing DB.
os.environ.setdefault("FLASK_ENV", "development")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # script lives in .critique_shots/, app.py is at repo root
SHOTS_DIR = REPO_ROOT / ".critique_shots"
PORT = 8765
ADMIN_USER_ID = "1"  # Sun Day Regrets (is_admin)

# (slug, method, path, form-data-or-None, auth). auth=True injects the admin
# session; login/register are public and redirect an authenticated user away, so
# they render logged-out (auth=False). All GET except the non-saving override-pick
# load_field POST, which renders Stage 2 without committing.
PAGES = [
    ("u3_make_pick", "GET", "/pick/20", None, True),
    ("u5_my_picks", "GET", "/my-picks", None, True),
    ("u7_login", "GET", "/login", None, False),
    ("u7_register", "GET", "/register", None, False),
    ("u7_change_password", "GET", "/change-password", None, True),
    ("u8_dashboard", "GET", "/admin", None, True),
    ("u9_override_stage1", "GET", "/admin/override-pick", None, True),
    # Stage 2: the non-saving load_field POST renders the field selects without committing.
    ("u9_override_stage2", "POST", "/admin/override-pick",
     {"tournament_id": "20", "user_id": "9", "load_field": "1"}, True),
    ("u10_tournaments", "GET", "/admin/tournaments", None, True),
    ("u10_users", "GET", "/admin/users", None, True),
    ("u10_payments", "GET", "/admin/payments", None, True),
]

# --- Green-gradient known-FP filter --------------------------------------
# The brand Augusta-pine navbar/footer gradient (style.css:95 --green-900 #00432e
# -> --green-800 #005c3f; :670 --green-800 -> --green-700 #006747; hue ~161deg) is
# misclassified by the detector's coarse green->cyan bucket as an `ai-color-palette`
# "Cyan gradient" AND trips `dark-glow` on the dark #00432e stop. Both are
# tool-classifier limitations, NOT design errors (decision 2026-05-27 — Pinehurst
# Pine stays; see findings-doc "Not in scope" + memory feedback-brand-over-linter).
# The CLI has no ignore flag, so we drop these two findings signature-tight:
#
#   * dark-glow  — the finding's own snippet carries the dark-green hex
#     ("Colored glow (#00432e) on dark background"), so we key on that hex directly.
#   * ai-color-palette "Cyan gradient" — the finding carries NO color/selector
#     (snippet is the bare "Cyan gradient background"), so we instead verify against
#     the source: drop it ONLY when EVERY gradient declared in style.css is a
#     brand-green gradient. If a genuinely-wrong (non-green) gradient is added later,
#     the CSS check fails and the finding is surfaced — never a loose "contains cyan".
#
# (Real schema confirmed empirically with impeccable 2.1.8: keys are antipattern /
# name / description / snippet — NOT the rule/message/selector the plan first guessed.)
GREEN_FP_COLORS = ("#00432e", "#005c3f")  # --green-900 / --green-800 (dark stops)
BRAND_GREEN_HEXES = ("#00432e", "#005c3f", "#006747", "#1a8a6a")  # --green-900/800/700/500
_STYLE_CSS = REPO_ROOT / "static" / "css" / "style.css"


def is_dark_glow_fp(finding: dict) -> bool:
    """dark-glow keyed to the brand dark-green hex in the finding's own snippet."""
    if finding.get("antipattern") != "dark-glow":
        return False
    blob = (finding.get("snippet", "") + finding.get("description", "")).lower()
    return any(c in blob for c in GREEN_FP_COLORS)


def _all_gradients_are_brand_green() -> bool:
    """True iff style.css declares >=1 gradient and every gradient is brand-green.

    Keys the cyan-gradient drop to the actual source signature, so a non-green
    gradient introduced later fails this check and the detector finding is kept.
    """
    try:
        css = _STYLE_CSS.read_text(encoding="utf-8")
    except OSError:
        return False
    import re

    gradients = re.findall(r"[a-z-]*gradient\s*\([^;]*\)", css, re.IGNORECASE)
    if not gradients:
        return False
    for g in gradients:
        low = g.lower()
        if "var(--green-" in low:
            continue
        if any(h in low for h in BRAND_GREEN_HEXES):
            continue
        return False  # an unrecognized (possibly real cyan) gradient — do not filter
    return True


def is_cyan_gradient_fp(finding: dict) -> bool:
    """ai-color-palette 'Cyan gradient' — drop only when CSS proves it's brand-green."""
    if finding.get("antipattern") != "ai-color-palette":
        return False
    blob = (finding.get("name", "") + finding.get("snippet", "")).lower()
    if "gradient" not in blob:
        return False
    return _all_gradients_are_brand_green()


def is_green_gradient_fp(finding: dict) -> bool:
    """True only for the brand-green navbar/footer gradient false positives."""
    return is_dark_glow_fp(finding) or is_cyan_gradient_fp(finding)


def filter_findings(findings: list) -> list:
    """Drop the known brand-green gradient false positives from a findings list."""
    return [f for f in findings if not is_green_gradient_fp(f)]


# --- Render ---------------------------------------------------------------
def render_pages():
    """Render each gated template through an admin-session test client."""
    from app import app

    app.config["WTF_CSRF_ENABLED"] = False  # in-process client only; live server untouched
    SHOTS_DIR.mkdir(exist_ok=True)
    written = []
    client = app.test_client()
    for slug, method, path, data, auth in PAGES:
        with client.session_transaction() as sess:
            if auth:
                sess["_user_id"] = ADMIN_USER_ID
            else:
                sess.pop("_user_id", None)
        resp = client.open(path, method=method, data=data)
        html = resp.get_data(as_text=True)
        out = SHOTS_DIR / f"{slug}.html"
        out.write_text(html, encoding="utf-8")
        written.append((slug, resp.status_code, len(html)))
    return written


# --- Serve + detect -------------------------------------------------------
@contextmanager
def serve_repo_root():
    """Serve the repo root over HTTP on PORT for the duration of the context."""
    handler = lambda *a, **kw: SimpleHTTPRequestHandler(*a, directory=str(REPO_ROOT), **kw)
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        time.sleep(0.5)
        yield
    finally:
        httpd.shutdown()


def detect(url: str) -> list:
    """Run impeccable detect --json against a URL; JSON is on stderr.

    A stalled CLI must not hang the batch, and one malformed payload must not
    abort it — so the subprocess is bounded by a timeout and every json.loads is
    guarded, returning [] on timeout or unparseable output.
    """
    try:
        proc = subprocess.run(
            ["impeccable", "detect", "--json", url],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return []
    raw = proc.stderr.strip() or proc.stdout.strip()
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        if start == -1:
            return []
        try:
            return json.loads(raw[start:])
        except json.JSONDecodeError:
            return []


def main():
    """Render the gated pages and (unless --render) detect + print post-filter counts."""
    render_only = "--render" in sys.argv
    written = render_pages()
    print("Rendered:")
    for slug, status, size in written:
        print(f"  {slug:24s} HTTP {status}  {size:,} bytes")
    if render_only:
        return
    print(f"\nDetecting via http://127.0.0.1:{PORT}/.critique_shots/<slug>.html\n")
    print(f"{'page':24s} {'raw':>4s} {'filtered':>9s}   findings (post-filter)")
    with serve_repo_root():
        for slug, *_ in PAGES:
            url = f"http://127.0.0.1:{PORT}/.critique_shots/{slug}.html"
            findings = detect(url)
            kept = filter_findings(findings)
            counts = {}
            for f in kept:
                counts[f.get("antipattern", "?")] = counts.get(f.get("antipattern", "?"), 0) + 1
            summary = ", ".join(f"{k}×{v}" for k, v in sorted(counts.items())) or "(clean)"
            print(f"{slug:24s} {len(findings):>4d} {len(kept):>9d}   {summary}")


if __name__ == "__main__":
    main()
