"""Render the profile README header and project cards (light + dark PNG).

Usage: python scripts/build_profile.py

Star counts come from the GitHub API and are rounded down, so re-running keeps
the cards current. The header art is a real hexdump of a chat request to the
FreeTheAI gateway.
"""

import html
import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

THEMES = {
    "dark": {"ink": "#f0f6fc", "text": "#d1d7e0", "muted": "#9198a1", "faint": "#3d444d",
             "card": "#151b23", "line": "#3d444d", "hex": "#3a4048", "hexhi": "#6e7681"},
    "light": {"ink": "#1f2328", "text": "#31363c", "muted": "#59636e", "faint": "#d1d9e0",
              "card": "#f6f8fa", "line": "#d1d9e0", "hex": "#d5dbe1", "hexhi": "#8c959f"},
}

# name, what it does, stack, link label, GitHub repo for the star count (or None)
CARDS = [
    ("GoonPAI", "Roleplay chat site I'm building on the FreeTheAI API.", "Go · Nuxt · PostgreSQL · Redis", "goonpai.chat", None),
    ("stealth-browser-mcp", "Lets AI agents drive a real Chrome browser.", "Python · FastMCP · CDP", None, "stealth-browser-mcp"),
    ("secrets.wtf", "Index of 181 AI servers left open on the internet.", "Internet-wide scanning", "secrets.wtf", None),
    ("UniClaudeProxy", "Runs Claude Code on OpenAI, Gemini, DeepSeek and Ollama.", "Python · FastAPI", None, "UniClaudeProxy"),
    ("unbuned", "Pulls the JavaScript back out of Bun executables.", "Python", None, "unbuned"),
    ("quickcontext", "Local code context engine for AI agents.", "Rust · Python", None, "quickcontext"),
]

REQUEST = (b"POST /v1/chat/completions HTTP/1.1\r\nHost: api.freetheai.org\r\n"
           b"Authorization: Bearer fta-****************\r\nContent-Type: application/json\r\n\r\n"
           b'{"model":"fta/auto","stream":true,"messages":[{"role":"user","content":"hi"}]}')

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:wght@400;600'
         '&family=IBM+Plex+Mono:wght@400;500&display=block" rel="stylesheet">')


def stars(repo: str) -> str:
    with urllib.request.urlopen(f"https://api.github.com/repos/vibheksoni/{repo}") as r:
        n = json.load(r)["stargazers_count"]
    if n >= 1000:
        return f"{n // 100 * 100:,}+ stars"
    if n >= 20:
        return f"{n // 10 * 10}+ stars"
    return "on GitHub"


def hexdump(data: bytes, rows: int) -> str:
    lines = []
    for i in range(0, min(len(data), rows * 16), 16):
        chunk = data[i:i + 16]
        hx = " ".join(f"{b:02x}" for b in chunk).ljust(47)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f'<span class="o">{i:04x}</span>  {hx}  <span class="a">{html.escape(asc)}</span>')
    return "\n".join(lines)


def page(theme: dict, body: str, css: str) -> str:
    t = theme
    return f"""<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>
* {{ box-sizing: border-box; margin: 0; }}
body {{ background: transparent; font-family: "Atkinson Hyperlegible Next", "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased; color: {t['text']}; }}
{css}</style></head><body>{body}</body></html>"""


def header(t: dict) -> str:
    css = f"""
#art {{ width: 1000px; height: 300px; position: relative; overflow: hidden; }}
pre {{ position: absolute; right: 0; top: 34px; font: 400 11.5px/1.75 "IBM Plex Mono", monospace; color: {t['hex']}; }}
pre .o {{ color: {t['faint']}; }} pre .a {{ color: {t['hexhi']}; }}
.who {{ position: absolute; left: 0; top: 70px; }}
h1 {{ font-size: 76px; font-weight: 600; line-height: 1; color: {t['ink']}; letter-spacing: -0.01em; }}
.role {{ margin-top: 18px; font-size: 26px; color: {t['text']}; }}
.line {{ margin-top: 8px; font-size: 20px; color: {t['muted']}; }}
"""
    body = f"""<div id="art"><pre>{hexdump(REQUEST, 11)}</pre>
<div class="who"><h1>Vibhek Soni</h1><p class="role">Backend engineer in New York</p>
<p class="line">API infrastructure and security tools</p></div></div>"""
    return page(t, body, css)


def card(t: dict, name: str, what: str, stack: str, meta: str) -> str:
    css = f"""
#art {{ width: 500px; height: 176px; padding: 26px 28px 24px; border: 1px solid {t['line']}; border-radius: 14px;
  background: {t['card']}; display: flex; flex-direction: column; }}
h2 {{ font-size: 27px; font-weight: 600; color: {t['ink']}; }}
.what {{ margin-top: 10px; font-size: 19px; line-height: 1.4; color: {t['text']}; }}
.foot {{ margin-top: auto; display: flex; justify-content: space-between; font: 400 14px/1 "IBM Plex Mono", monospace; color: {t['muted']}; }}
"""
    body = f"""<div id="art"><h2>{html.escape(name)}</h2><p class="what">{html.escape(what)}</p>
<div class="foot"><span>{html.escape(stack)}</span><span>{html.escape(meta)}</span></div></div>"""
    return page(t, body, css)


def main() -> None:
    metas = [label or stars(repo) for _, _, _, label, repo in CARDS]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page_ = browser.new_page(device_scale_factor=2, viewport={"width": 1100, "height": 400})
        for name, t in THEMES.items():
            page_.set_content(header(t), wait_until="networkidle")
            page_.evaluate("document.fonts.ready")
            page_.locator("#art").screenshot(path=str(OUT / f"header-{name}.png"), omit_background=True)
            for (title, what, stack, _, _), meta in zip(CARDS, metas):
                slug = title.lower().replace(".", "-")
                page_.set_content(card(t, title, what, stack, meta), wait_until="networkidle")
                page_.evaluate("document.fonts.ready")
                page_.locator("#art").screenshot(path=str(OUT / f"card-{slug}-{name}.png"), omit_background=True)
        browser.close()
    print(json.dumps(dict(zip([c[0] for c in CARDS], metas)), indent=2))


if __name__ == "__main__":
    main()
