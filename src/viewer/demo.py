"""Launch the committed synthetic episode-viewer demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.viewer.webapp import DEFAULT_PORT, main as run_viewer

DEMO_DIR = Path(__file__).resolve().parents[2] / "examples" / "episode-viewer-demo"
DEMO_EVENTS = DEMO_DIR / "events.jsonl"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="episode-viewer-demo",
        description="Open the included synthetic episode-viewer demo."
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if not DEMO_EVENTS.is_file():
        raise SystemExit(f"committed demo data is missing: {DEMO_EVENTS}")
    run_viewer(
        [
            "--input",
            str(DEMO_EVENTS),
            "--source-kind",
            "synthetic",
            "--show-transcripts",
            "--port",
            str(args.port),
        ]
    )


if __name__ == "__main__":
    main()
