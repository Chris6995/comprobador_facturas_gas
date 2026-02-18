#!/usr/bin/env python3
"""Entry point for packaged Streamlit app."""

from __future__ import annotations

from pathlib import Path
import sys

from streamlit.web import cli as stcli


def _app_path() -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_dir / "app_chatgpt.py"


def main() -> int:
    app_path = _app_path()
    if not app_path.exists():
        raise FileNotFoundError(f"App not found: {app_path}")

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    return stcli.main()


if __name__ == "__main__":
    raise SystemExit(main())
