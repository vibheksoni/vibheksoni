"""Render the FreeTheAI request-path diagram (light + dark PNG) with live numbers.

Usage: python scripts/build_assets.py

Token and request totals come from the public stats page at freetheai.org/stats,
so re-running this keeps the diagram footer current.
"""

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "assets" / "src" / "freetheai-diagram.html"
OUT_DIR = ROOT / "assets"


def round_down(value: float, unit: str) -> str:
    if value >= 100:
        return f"{int(value)}{unit}+"
    return f"{int(value * 10) / 10:g}{unit}+"


def freetheai_stats(page) -> dict:
    page.goto("https://freetheai.org/stats", wait_until="networkidle")
    page.wait_for_selector("text=Tokens served", timeout=30_000)
    text = page.inner_text("body")
    tokens = re.search(r"Tokens served\s+([\d.]+)\s*([KMB])", text)
    requests = re.search(r"Requests served\s+([\d.]+)\s*([KMB])", text)
    if not (tokens and requests):
        raise RuntimeError("Could not read FreeTheAI stats page")
    return {
        "tokens": round_down(float(tokens.group(1)), tokens.group(2)),
        "requests": round_down(float(requests.group(1)), requests.group(2)),
    }


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        values = freetheai_stats(browser.new_page())
        html = TEMPLATE.read_text(encoding="utf-8")
        for key, value in values.items():
            html = html.replace("{{" + key + "}}", value)

        render = browser.new_page(device_scale_factor=2, viewport={"width": 900, "height": 600})
        for theme in ("light", "dark"):
            render.set_content(html.replace("<body>", f'<body data-theme="{theme}">'), wait_until="networkidle")
            render.evaluate("document.fonts.ready")
            render.locator("#card").screenshot(path=str(OUT_DIR / f"freetheai-{theme}.png"), omit_background=True)
        browser.close()

    print(json.dumps(values, indent=2))


if __name__ == "__main__":
    main()
