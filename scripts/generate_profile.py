#!/usr/bin/env python3
"""Generate profile SVG assets for the GitHub profile README.

Produces theme-paired SVGs under assets/profile/:
  hero-{dark,light}.svg          identity hero
  proof-{dark,light}.svg         proof strip (live metrics)
  card-<slug>-{dark,light}.svg   one card per flagship project (linkable)
  stack-{dark,light}.svg         core stack strip

Runs locally or in GitHub Actions. Stdlib only.
Metrics come from the GitHub API when GITHUB_TOKEN is present; otherwise
the committed assets/profile/metrics.json is the fallback so the README
always renders with the last known values.

SVG constraints honored (github/markup sanitizer + browser image rules):
  - presentation attributes only, no <style>, no scripts, no external refs
  - no SMIL/CSS animation (rendering is inconsistent across browsers)
  - system font stacks, no embedded fonts
  - no links inside SVGs (SVG-as-image cannot contain working links)
"""

import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets" / "profile"
ICON_DIR = ROOT / "scripts"
METRICS_FILE = ASSETS / "metrics.json"

FONT_SANS = "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONT_MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"

THEMES = {
    "dark": {
        "panel": "#161b22",
        "hairline": "#30363d",
        "fg": "#e6edf3",
        "muted": "#8b949e",
        "accent": "#58a6ff",
        "green": "#3fb950",
        "chip": "#21262d",
    },
    "light": {
        "panel": "#f6f8fa",
        "hairline": "#d0d7de",
        "fg": "#1f2328",
        "muted": "#57606a",
        "accent": "#0969da",
        "green": "#1a7f37",
        "chip": "#eaeef2",
    },
}

PROJECTS = [
    {
        "slug": "stealth-browser-mcp",
        "name": "stealth-browser-mcp",
        "category": "BROWSER AUTOMATION",
        "desc": "MCP browser automation and CDP instrumentation for agent workflows.",
        "tech": "Python · MCP · CDP · browser automation",
        "repo": "vibheksoni/stealth-browser-mcp",
        "metric": "stars_forks",
        "url": "https://github.com/vibheksoni/stealth-browser-mcp",
    },
    {
        "slug": "freetheai",
        "name": "FreeTheAI",
        "category": "AI INFRASTRUCTURE",
        "desc": "OpenAI-compatible AI API with 50+ models, streaming, tools, images, Messages, and Responses.",
        "tech": "API infrastructure · model routing · auth · usage tracking",
        "repo": None,
        "metric": "models",
        "url": "https://freetheai.xyz/",
    },
    {
        "slug": "stock-assist",
        "name": "Stock Assist",
        "category": "PRODUCT · SAAS",
        "desc": "Production AI financial-analysis SaaS built end to end with realtime market data.",
        "tech": "Python · Flask · Redis · MySQL · WebSockets",
        "repo": "vibheksoni/stock-assist",
        "metric": "users",
        "url": "https://github.com/vibheksoni/stock-assist",
    },
    {
        "slug": "verbalcodeai",
        "name": "VerbalCodeAI",
        "category": "DEVELOPER TOOLING",
        "desc": "Local code intelligence for indexing, retrieval, and terminal-first codebase navigation.",
        "tech": "Python · embeddings · retrieval · CLI",
        "repo": "vibheksoni/VerbalCodeAi",
        "metric": "stars_forks",
        "url": "https://github.com/vibheksoni/VerbalCodeAi",
    },
    {
        "slug": "unbuned",
        "name": "unbuned",
        "category": "REVERSE ENGINEERING",
        "desc": "Zero-dependency tool for recovering JavaScript from Bun executables.",
        "tech": "Python · binary analysis · reverse engineering",
        "repo": "vibheksoni/unbuned",
        "metric": "stars_forks",
        "url": "https://github.com/vibheksoni/unbuned",
    },
]

STACK = [
    ("Python", "python"),
    ("FastAPI", "fastapi"),
    ("Flask", "flask"),
    ("PostgreSQL", "postgresql"),
    ("Redis", "redis"),
    ("Docker", "docker"),
    ("Linux", "linux"),
    ("Rust", "rust"),
    ("MCP", None),
]


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def load_icon_path(slug: str) -> str:
    path = ICON_DIR / f"icon-{slug}.svg"
    if not path.exists():
        return ""
    match = re.search(r'<path d="([^"]+)"', path.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def format_stars(value: int) -> str:
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return str(value)


def svg_header(width: int, height: int, title: str, desc: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-labelledby="t d">',
        f"  <title id=\"t\">{esc(title)}</title>",
        f"  <desc id=\"d\">{esc(desc)}</desc>",
    ]


def svg_footer() -> list[str]:
    return ["</svg>"]


def render_hero(theme: str) -> str:
    c = THEMES[theme]
    lines = svg_header(
        900, 240,
        "Vibhek Soni, backend systems and AI infrastructure",
        "Vibhek Soni. Backend systems, AI infrastructure, and security research. Open to backend and AI infrastructure opportunities.",
    )
    lines.append(f'  <text x="40" y="78" font-family="{FONT_SANS}" font-size="36" font-weight="700" fill="{c["fg"]}">Vibhek Soni</text>')
    lines.append(f'  <text x="40" y="112" font-family="{FONT_SANS}" font-size="17" fill="{c["muted"]}">Backend systems · AI infrastructure · security research</text>')
    lines.append(f'  <text x="40" y="142" font-family="{FONT_MONO}" font-size="12" fill="{c["muted"]}">NEW YORK CITY · PYTHON · FASTAPI · MCP · PROTOCOL ANALYSIS</text>')
    lines.append(f'  <rect x="40" y="164" width="360" height="34" rx="17" fill="{c["chip"]}" stroke="{c["hairline"]}"/>')
    lines.append(f'  <circle cx="62" cy="181" r="5" fill="{c["green"]}"/>')
    lines.append(f'  <text x="78" y="186" font-family="{FONT_SANS}" font-size="14" fill="{c["fg"]}">Open to backend / AI infrastructure</text>')
    cx0, cy0 = 640, 100
    nodes = [("API", 780, 52), ("AGENTS", 800, 148), ("DATA", 660, 178)]
    for nx, ny in [(n[1], n[2]) for n in nodes]:
        lines.append(f'  <line x1="{cx0}" y1="{cy0}" x2="{nx}" y2="{ny}" stroke="{c["hairline"]}" stroke-width="1.5"/>')
    lines.append(f'  <rect x="{cx0 - 44}" y="{cy0 - 22}" width="88" height="44" rx="10" fill="{c["panel"]}" stroke="{c["accent"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{cx0}" y="{cy0 + 4}" text-anchor="middle" font-family="{FONT_MONO}" font-size="11" fill="{c["accent"]}">ROUTER</text>')
    for label, nx, ny in nodes:
        lines.append(f'  <rect x="{nx - 46}" y="{ny - 18}" width="92" height="36" rx="8" fill="{c["panel"]}" stroke="{c["hairline"]}"/>')
        lines.append(f'  <text x="{nx}" y="{ny + 4}" text-anchor="middle" font-family="{FONT_MONO}" font-size="10.5" fill="{c["muted"]}">{label}</text>')
    lines.extend(svg_footer())
    return "\n".join(lines) + "\n"


def render_proof(theme: str, metrics: dict) -> str:
    c = THEMES[theme]
    stealth = metrics.get("stealth_browser_mcp", {})
    stars = stealth.get("stars", 1598)
    forks = stealth.get("forks", 242)
    users = metrics.get("stock_assist", {}).get("users", 46)
    models = metrics.get("freetheai", {}).get("models", "50+")
    lines = svg_header(
        900, 104,
        "Open source traction, production users, and AI infrastructure",
        "stealth-browser-mcp stars and forks, Stock Assist production users, and FreeTheAI models.",
    )
    blocks = [
        ("OPEN SOURCE", format_stars(stars), f"stars · {forks} forks", "stealth-browser-mcp"),
        ("PRODUCTION", str(users), "active users", "Stock Assist"),
        ("AI INFRA", str(models), "models", "FreeTheAI"),
    ]
    for (label, value, sub, name), cx in zip(blocks, (150, 450, 750)):
        lines.append(f'  <text x="{cx}" y="30" text-anchor="middle" font-family="{FONT_MONO}" font-size="11" letter-spacing="1.5" fill="{c["muted"]}">{label}</text>')
        lines.append(f'  <text x="{cx}" y="62" text-anchor="middle" font-family="{FONT_SANS}" font-size="26" font-weight="700" fill="{c["fg"]}">{value}</text>')
        lines.append(f'  <text x="{cx}" y="84" text-anchor="middle" font-family="{FONT_MONO}" font-size="11" fill="{c["muted"]}">{sub}</text>')
        lines.append(f'  <text x="{cx}" y="99" text-anchor="middle" font-family="{FONT_SANS}" font-size="12" fill="{c["accent"]}">{name}</text>')
    lines.append(f'  <line x1="300" y1="14" x2="300" y2="90" stroke="{c["hairline"]}" stroke-width="1"/>')
    lines.append(f'  <line x1="600" y1="14" x2="600" y2="90" stroke="{c["hairline"]}" stroke-width="1"/>')
    lines.extend(svg_footer())
    return "\n".join(lines) + "\n"


def project_metric(project: dict, metrics: dict) -> tuple[str, str]:
    kind = project["metric"]
    if kind == "stars_forks":
        repo = project["repo"]
        data = {}
        for key, candidate in (
            ("stealth_browser_mcp", "vibheksoni/stealth-browser-mcp"),
            ("verbalcodeai", "vibheksoni/VerbalCodeAi"),
            ("unbuned", "vibheksoni/unbuned"),
        ):
            if candidate == repo:
                data = metrics.get(key, {})
        stars = data.get("stars", 0)
        forks = data.get("forks", 0)
        return format_stars(stars), f"stars · {forks} forks"
    if kind == "users":
        return str(metrics.get("stock_assist", {}).get("users", 46)), "users · production SaaS"
    if kind == "models":
        return str(metrics.get("freetheai", {}).get("models", "50+")), "models · live API"
    return "", ""


def render_card(project: dict, theme: str, metrics: dict) -> str:
    c = THEMES[theme]
    value, label = project_metric(project, metrics)
    lines = svg_header(
        900, 88,
        project["name"],
        project["desc"],
    )
    lines.append(f'  <rect x="0" y="0" width="900" height="88" rx="10" fill="{c["panel"]}" stroke="{c["hairline"]}"/>')
    lines.append(f'  <text x="24" y="24" font-family="{FONT_MONO}" font-size="10.5" letter-spacing="1.2" fill="{c["muted"]}">{esc(project["category"])}</text>')
    lines.append(f'  <text x="24" y="46" font-family="{FONT_SANS}" font-size="16.5" font-weight="700" fill="{c["fg"]}">{esc(project["name"])}</text>')
    lines.append(f'  <text x="24" y="66" font-family="{FONT_SANS}" font-size="13" fill="{c["muted"]}">{esc(project["desc"])}</text>')
    lines.append(f'  <text x="24" y="82" font-family="{FONT_MONO}" font-size="11" fill="{c["muted"]}">{esc(project["tech"])}</text>')
    lines.append(f'  <text x="876" y="46" text-anchor="end" font-family="{FONT_SANS}" font-size="18" font-weight="700" fill="{c["accent"]}">{esc(value)}</text>')
    lines.append(f'  <text x="876" y="64" text-anchor="end" font-family="{FONT_MONO}" font-size="10.5" fill="{c["muted"]}">{esc(label)}</text>')
    lines.extend(svg_footer())
    return "\n".join(lines) + "\n"


def render_stack(theme: str) -> str:
    c = THEMES[theme]
    lines = svg_header(900, 208, "Core stack", "Python, FastAPI, Flask, PostgreSQL, Redis, Docker, Linux, Rust, and MCP.")
    positions = [
        (160, 56), (450, 56), (740, 56),
        (160, 120), (450, 120), (740, 120),
        (160, 184), (450, 184), (740, 184),
    ]
    for (label, slug), (cx, cy) in zip(STACK, positions):
        if slug:
            d = load_icon_path(slug)
            lines.append(f'  <path d="{d}" transform="translate({cx - 76},{cy - 10}) scale(0.83)" fill="{c["muted"]}"/>')
            lines.append(f'  <text x="{cx - 52}" y="{cy + 4}" font-family="{FONT_SANS}" font-size="14" fill="{c["fg"]}">{label}</text>')
        else:
            lines.append(f'  <rect x="{cx - 84}" y="{cy - 18}" width="168" height="36" rx="18" fill="{c["chip"]}" stroke="{c["hairline"]}"/>')
            lines.append(f'  <text x="{cx}" y="{cy + 4}" text-anchor="middle" font-family="{FONT_SANS}" font-size="13.5" fill="{c["fg"]}">{label}</text>')
    lines.extend(svg_footer())
    return "\n".join(lines) + "\n"


def fetch_live_metrics() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    repos = {
        "stealth_browser_mcp": "vibheksoni/stealth-browser-mcp",
        "verbalcodeai": "vibheksoni/VerbalCodeAi",
        "unbuned": "vibheksoni/unbuned",
    }
    result = {}
    for key, full_name in repos.items():
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{full_name}", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            result[key] = {"stars": data.get("stargazers_count", 0), "forks": data.get("forks_count", 0)}
        except Exception:
            continue
    result["stock_assist"] = {"users": 46}
    result["freetheai"] = {"models": "50+"}
    return result


def main() -> int:
    existing = {}
    if METRICS_FILE.exists():
        existing = json.loads(METRICS_FILE.read_text(encoding="utf-8"))

    metrics = fetch_live_metrics()
    for key, fallback in existing.items():
        metrics.setdefault(key, fallback)
    metrics.setdefault("stock_assist", {"users": 46})
    metrics.setdefault("freetheai", {"models": "50+"})
    metrics["generated_at"] = existing.get("generated_at", "2026-08-19")

    ASSETS.mkdir(parents=True, exist_ok=True)

    for theme in ("dark", "light"):
        (ASSETS / f"hero-{theme}.svg").write_text(render_hero(theme), encoding="utf-8")
        (ASSETS / f"proof-{theme}.svg").write_text(render_proof(theme, metrics), encoding="utf-8")
        (ASSETS / f"stack-{theme}.svg").write_text(render_stack(theme), encoding="utf-8")
        for project in PROJECTS:
            out = ASSETS / f"card-{project['slug']}-{theme}.svg"
            out.write_text(render_card(project, theme, metrics), encoding="utf-8")
            print(f"wrote {out.relative_to(ROOT)}")

    METRICS_FILE.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {METRICS_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
