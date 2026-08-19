#!/usr/bin/env python3
"""Generate profile SVG assets for the GitHub profile README.

Produces theme-paired SVGs under assets/profile/:
  hero-{dark,light}.svg          identity hero with flow diagram
  proof-{dark,light}.svg         contained proof strip (live metrics)
  card-<slug>-{dark,light}.svg   one card per flagship project (linkable)
  stack-{dark,light}.svg         system-oriented stack pipeline

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
        "desc": ["MCP browser automation and CDP", "instrumentation for agent workflows."],
        "tech": "Python · MCP · CDP · automation",
        "repo": "vibheksoni/stealth-browser-mcp",
        "metric": "stars_forks",
        "motif": ["browser", "CDP", "agent"],
        "url": "https://github.com/vibheksoni/stealth-browser-mcp",
    },
    {
        "slug": "freetheai",
        "name": "FreeTheAI",
        "category": "AI INFRASTRUCTURE",
        "desc": ["OpenAI-compatible API with 60+", "models, streaming, tools, images."],
        "tech": "API · model routing · auth · usage",
        "repo": None,
        "metric": "models",
        "motif": ["providers", "router", "API"],
        "url": "https://freetheai.xyz/",
    },
    {
        "slug": "stock-assist",
        "name": "Stock Assist",
        "category": "PRODUCT · SAAS",
        "desc": ["Production AI financial analysis", "SaaS with realtime market data."],
        "tech": "Python · Flask · Redis · MySQL · WebSockets",
        "repo": "vibheksoni/stock-assist",
        "metric": "users",
        "motif": ["market", "AI", "user"],
        "url": "https://github.com/vibheksoni/stock-assist",
    },
    {
        "slug": "verbalcodeai",
        "name": "VerbalCodeAI",
        "category": "DEVELOPER TOOLING",
        "desc": ["Local code intelligence for", "indexing and terminal search."],
        "tech": "Python · embeddings · retrieval · CLI",
        "repo": "vibheksoni/VerbalCodeAi",
        "metric": "stars_forks",
        "motif": ["files", "index", "retrieval"],
        "url": "https://github.com/vibheksoni/VerbalCodeAi",
    },
    {
        "slug": "unbuned",
        "name": "unbuned",
        "category": "REVERSE ENGINEERING",
        "desc": ["Zero-dependency tool for recovering", "JavaScript from Bun executables."],
        "tech": "Python · binary analysis · RE",
        "repo": "vibheksoni/unbuned",
        "metric": "stars_forks",
        "motif": ["exe", "analysis", "JS"],
        "url": "https://github.com/vibheksoni/unbuned",
    },
    {
        "slug": "more-work",
        "name": "More engineering and research",
        "category": "MORE WORK",
        "desc": ["UniClaudeProxy, t3router, youtube-ai,", "crawl, secrets-wtf, and more."],
        "tech": "developer infrastructure · protocol clients · security research",
        "repo": None,
        "metric": "none",
        "motif": None,
        "url": "https://github.com/vibheksoni#more-engineering-and-research",
    },
]

STACK_FLOW = [
    ("Python", "python", "PYTHON"),
    ("FastAPI", "fastapi", "FASTAPI"),
    ("PostgreSQL", "postgresql", "POSTGRES"),
    ("Redis", "redis", "REDIS"),
    ("Docker", "docker", "DOCKER"),
    ("Linux", "linux", "LINUX"),
]
STACK_FLOW_CENTERS = [90, 240, 390, 510, 660, 800]
STACK_FLOW_ARROWS = [(90, 240), (240, 390), (510, 660), (660, 800)]
SECONDARY = [("Rust", "rust"), ("MCP", None)]


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


def flow_arrow(lines: list[str], c: dict, x1: int, x2: int, y: int) -> None:
    lines.append(f'  <line x1="{x1}" y1="{y}" x2="{x2 - 6}" y2="{y}" stroke="{c["hairline"]}" stroke-width="1.5"/>')
    lines.append(f'  <polygon points="{x2 - 6},{y - 4} {x2},{y} {x2 - 6},{y + 4}" fill="{c["muted"]}"/>')


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
    # Flow diagram: client -> protocol -> router -> api/agents/data
    nodes = [
        ("CLIENT", 560, 120, False),
        ("PROTOCOL", 632, 120, False),
        ("ROUTER", 712, 120, True),
        ("API", 815, 58, False),
        ("AGENTS", 815, 120, False),
        ("DATA", 815, 182, False),
    ]
    links = [(560, 632, 120), (632, 712, 120), (712, 815, 58), (712, 815, 120), (712, 815, 182)]
    for x1, x2, y in links:
        flow_arrow(lines, c, x1 + 26, x2 - 26, y)
    for label, nx, ny, accent in nodes:
        stroke = c["accent"] if accent else c["hairline"]
        fill = c["accent"] if accent else c["panel"]
        lines.append(f'  <rect x="{nx - 27}" y="{ny - 14}" width="54" height="28" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        lines.append(f'  <text x="{nx}" y="{ny + 4}" text-anchor="middle" font-family="{FONT_MONO}" font-size="9.5" fill="{c["fg"]}">{label}</text>')
    lines.extend(svg_footer())
    return "\n".join(lines) + "\n"


def render_proof(theme: str, metrics: dict) -> str:
    c = THEMES[theme]
    stealth = metrics.get("stealth_browser_mcp", {})
    stars = stealth.get("stars", 1598)
    forks = stealth.get("forks", 242)
    users = metrics.get("stock_assist", {}).get("users", 46)
    models = metrics.get("freetheai", {}).get("models", "60+")
    lines = svg_header(
        900, 100,
        "Open source traction, production users, and AI infrastructure",
        "stealth-browser-mcp stars and forks, Stock Assist production users, and FreeTheAI active models.",
    )
    lines.append(f'  <rect x="0" y="0" width="900" height="100" rx="10" fill="{c["panel"]}" stroke="{c["hairline"]}"/>')
    blocks = [
        ("OPEN SOURCE", format_stars(stars), f"stars · {forks} forks", "stealth-browser-mcp"),
        ("PRODUCTION", str(users), "active users", "Stock Assist"),
        ("AI INFRA", str(models), "active models", "FreeTheAI"),
    ]
    for (label, value, sub, name), cx in zip(blocks, (150, 450, 750)):
        lines.append(f'  <text x="{cx}" y="28" text-anchor="middle" font-family="{FONT_MONO}" font-size="9" letter-spacing="1.5" fill="{c["muted"]}">{label}</text>')
        lines.append(f'  <text x="{cx}" y="60" text-anchor="middle" font-family="{FONT_SANS}" font-size="24" font-weight="700" fill="{c["fg"]}">{value}</text>')
        lines.append(f'  <text x="{cx}" y="78" text-anchor="middle" font-family="{FONT_MONO}" font-size="10" fill="{c["muted"]}">{sub}</text>')
        lines.append(f'  <text x="{cx}" y="93" text-anchor="middle" font-family="{FONT_SANS}" font-size="11" fill="{c["accent"]}">{name}</text>')
    lines.append(f'  <line x1="300" y1="14" x2="300" y2="86" stroke="{c["hairline"]}" stroke-width="1"/>')
    lines.append(f'  <line x1="600" y1="14" x2="600" y2="86" stroke="{c["hairline"]}" stroke-width="1"/>')
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
        return str(metrics.get("freetheai", {}).get("models", "60+")), "active models"
    return "", ""


def render_motif(lines: list[str], c: dict, labels: list[str]) -> None:
    if not labels:
        dots = "  ".join(["·"] * 3)
        lines.append(f'  <text x="220" y="162" text-anchor="middle" font-family="{FONT_SANS}" font-size="16" fill="{c["muted"]}">{dots}</text>')
        return
    centers = [96, 220, 344]
    for i, (label, cx) in enumerate(zip(labels, centers)):
        accent = i == 1
        stroke = c["accent"] if accent else c["hairline"]
        lines.append(f'  <rect x="{cx - 24}" y="150" width="48" height="24" rx="6" fill="{c["chip"]}" stroke="{stroke}" stroke-width="1.2"/>')
        lines.append(f'  <text x="{cx}" y="166" text-anchor="middle" font-family="{FONT_MONO}" font-size="8.5" fill="{c["fg"]}">{esc(label)}</text>')
    for x1, x2 in [(120, 172), (244, 296)]:
        lines.append(f'  <line x1="{x1}" y1="162" x2="{x2}" y2="162" stroke="{c["hairline"]}" stroke-width="1.2"/>')
        lines.append(f'  <polygon points="{x2},{159} {x2 + 4},{162} {x2},{165}" fill="{c["muted"]}"/>')


def render_card(project: dict, theme: str, metrics: dict) -> str:
    c = THEMES[theme]
    value, label = project_metric(project, metrics)
    lines = svg_header(440, 200, project["name"], project["desc"][0] + " " + project["desc"][1])
    lines.append(f'  <rect x="0" y="0" width="440" height="200" rx="12" fill="{c["panel"]}" stroke="{c["hairline"]}"/>')
    lines.append(f'  <text x="18" y="26" font-family="{FONT_MONO}" font-size="9" letter-spacing="1.2" fill="{c["muted"]}">{esc(project["category"])}</text>')
    if value:
        lines.append(f'  <text x="422" y="28" text-anchor="end" font-family="{FONT_SANS}" font-size="19" font-weight="700" fill="{c["accent"]}">{esc(value)}</text>')
        lines.append(f'  <text x="422" y="44" text-anchor="end" font-family="{FONT_MONO}" font-size="8.5" fill="{c["muted"]}">{esc(label)}</text>')
    lines.append(f'  <text x="18" y="66" font-family="{FONT_SANS}" font-size="15" font-weight="700" fill="{c["fg"]}">{esc(project["name"])}</text>')
    y = 86
    for line in project["desc"]:
        lines.append(f'  <text x="18" y="{y}" font-family="{FONT_SANS}" font-size="11.5" fill="{c["muted"]}">{esc(line)}</text>')
        y += 15
    lines.append(f'  <text x="18" y="120" font-family="{FONT_MONO}" font-size="9.5" fill="{c["muted"]}">{esc(project["tech"])}</text>')
    render_motif(lines, c, project["motif"])
    lines.extend(svg_footer())
    return "\n".join(lines) + "\n"


def render_stack(theme: str) -> str:
    c = THEMES[theme]
    lines = svg_header(
        900, 176,
        "Core stack",
        "Python to FastAPI to PostgreSQL and Redis, packaged with Docker on Linux. Rust and MCP as secondary capabilities.",
    )
    lines.append(f'  <text x="40" y="22" font-family="{FONT_MONO}" font-size="9" letter-spacing="1.5" fill="{c["muted"]}">PRIMARY PIPELINE</text>')
    for (label, slug, _mono), cx in zip(STACK_FLOW, STACK_FLOW_CENTERS):
        d = load_icon_path(slug)
        lines.append(f'  <path d="{d}" transform="translate({cx - 66},{36}) scale(0.8)" fill="{c["muted"]}"/>')
        lines.append(f'  <text x="{cx - 40}" y="56" font-family="{FONT_SANS}" font-size="13" fill="{c["fg"]}">{label}</text>')
    for x1, x2 in STACK_FLOW_ARROWS:
        flow_arrow(lines, c, x1 + 62, x2 - 62, 52)
    lines.append(f'  <line x1="40" y1="92" x2="860" y2="92" stroke="{c["hairline"]}" stroke-width="1"/>')
    lines.append(f'  <text x="40" y="122" font-family="{FONT_MONO}" font-size="9" letter-spacing="1.5" fill="{c["muted"]}">SECONDARY CAPABILITIES</text>')
    for label, slug, cx in [("Rust", "rust", 380), ("MCP", None, 520)]:
        if slug:
            d = load_icon_path(slug)
            lines.append(f'  <rect x="{cx - 60}" y="138" width="120" height="30" rx="15" fill="{c["chip"]}" stroke="{c["hairline"]}"/>')
            lines.append(f'  <path d="{d}" transform="translate({cx - 46},{142}) scale(0.75)" fill="{c["muted"]}"/>')
            lines.append(f'  <text x="{cx - 30}" y="158" font-family="{FONT_SANS}" font-size="12" fill="{c["fg"]}">{label}</text>')
        else:
            lines.append(f'  <rect x="{cx - 60}" y="138" width="120" height="30" rx="15" fill="{c["chip"]}" stroke="{c["hairline"]}"/>')
            lines.append(f'  <text x="{cx}" y="158" text-anchor="middle" font-family="{FONT_SANS}" font-size="12" fill="{c["fg"]}">{label}</text>')
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
    # Static, already verified public facts.
    result["stock_assist"] = {"users": 46}
    result["freetheai"] = {"models": "60+"}
    return result


def main() -> int:
    existing = {}
    if METRICS_FILE.exists():
        existing = json.loads(METRICS_FILE.read_text(encoding="utf-8"))

    metrics = fetch_live_metrics()
    for key, fallback in existing.items():
        metrics.setdefault(key, fallback)
    metrics.setdefault("stock_assist", {"users": 46})
    metrics.setdefault("freetheai", {"models": "60+"})
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
