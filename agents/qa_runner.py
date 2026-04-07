"""
QA Runner

Executes a test command inside the project directory, captures all output,
and renders it as a terminal-style PNG to send back via Telegram.
"""

from __future__ import annotations
import asyncio
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_TIMEOUT = 120   # seconds per test run

# ─── Terminal colour palette (GitHub Dark theme) ─────────────────────────────
_BG     = (13,  17,  23)
_FG     = (201, 209, 217)
_GREEN  = (63,  185, 80)
_RED    = (248, 81,  73)
_YELLOW = (210, 153, 34)
_BLUE   = (88,  166, 255)
_GREY   = (110, 118, 129)

_PADDING = 20
_LINE_H  = 20
_FONT_SZ = 13


# ─── Font loader ─────────────────────────────────────────────────────────────

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        # Linux (Dockerfile installs this)
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        # macOS
        "/System/Library/Fonts/Menlo.ttc",
        # Windows
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    # Pillow ≥10: load_default supports size
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# ─── Image renderer ──────────────────────────────────────────────────────────

def render_terminal(output: str, passed: bool | None, command: str = "") -> bytes:
    """Render terminal output as a PNG and return the raw bytes."""
    font  = _load_font(_FONT_SZ)
    lines = output.splitlines() or ["(no output)"]

    # Truncate very long output
    if len(lines) > 100:
        lines = lines[:45] + ["", f"  ... {len(lines) - 90} lines omitted ...", ""] + lines[-45:]

    header = [
        f"  SE-Agents QA Runner",
        f"  $ {command}" if command else "",
        "  " + "─" * 58,
        "",
    ]
    if passed is None:
        status_text  = "  ⚠  NO TEST COMMAND"
        status_color = _YELLOW
    elif passed:
        status_text  = "  ✓  ALL TESTS PASSED"
        status_color = _GREEN
    else:
        status_text  = "  ✗  TESTS FAILED"
        status_color = _RED

    footer = ["", "  " + "─" * 58, status_text]

    all_lines = header + lines + footer

    # Measure width from longest line
    dummy = Image.new("RGB", (1, 1))
    dd = ImageDraw.Draw(dummy)
    max_w = max(
        (dd.textlength(ln, font=font) if ln else 0)
        for ln in all_lines
    )
    width  = int(max_w) + _PADDING * 2
    width  = max(width, 640)
    height = len(all_lines) * _LINE_H + _PADDING * 2

    img  = Image.new("RGB", (width, height), _BG)
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(all_lines):
        y = _PADDING + i * _LINE_H
        if i == 0:
            color = _BLUE           # title
        elif i == 1 and command:
            color = _GREY           # command
        elif i == len(all_lines) - 1:
            color = status_color    # status
        else:
            # Colour-hint common patterns
            ll = line.lower()
            if any(k in ll for k in ("error", "fail", "exception", "traceback")):
                color = _RED
            elif any(k in ll for k in ("pass", "ok", "success", "✓")):
                color = _GREEN
            elif any(k in ll for k in ("warn", "skip", "deprecat")):
                color = _YELLOW
            else:
                color = _FG
        draw.text((_PADDING, y), line, font=font, fill=color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ─── Public API ──────────────────────────────────────────────────────────────

async def run_tests(project_path: str, test_command: str) -> dict:
    """
    Run test_command inside project_path and return:
        {
            "passed":     bool | None,
            "output":     str,
            "screenshot": bytes,   # PNG
        }
    """
    if not test_command.strip():
        img = render_terminal("No test command was provided.", None)
        return {"passed": None, "output": "No test command.", "screenshot": img}

    root = Path(project_path)

    proc = await asyncio.create_subprocess_shell(
        test_command,
        cwd=str(root),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=_TIMEOUT)
        output = stdout.decode(errors="replace")
        passed = proc.returncode == 0
    except asyncio.TimeoutError:
        proc.kill()
        output = f"[TIMEOUT] Test run exceeded {_TIMEOUT}s and was killed."
        passed = False

    screenshot = render_terminal(output, passed, test_command)
    return {"passed": passed, "output": output, "screenshot": screenshot}
