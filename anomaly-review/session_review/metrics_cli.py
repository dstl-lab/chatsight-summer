"""Calculate evidence-linked metrics from a saved question-session report."""
import argparse
import json
from pathlib import Path

from .metrics import MetricsConfig, calculate_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--active-interval-seconds", type=int, default=300)
    args = parser.parse_args()
    try:
        source = json.loads(args.input.read_bytes())
        if source.get("method") != "question-episodes-v1":
            raise ValueError("Expected a question-episodes-v1 report.")
        result = calculate_metrics(source, MetricsConfig(args.active_interval_seconds))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            json.dump(result, file, indent=2, ensure_ascii=True, allow_nan=False)
            file.write("\n")
    except (OSError, ValueError, TypeError, KeyError):
        parser.exit(2, "Cannot process input or create output; existing output is never overwritten.\n")
    print(json.dumps({"origin": result["origin"], "episodes": len(result["episodes"]),
                      "method": result["method"]}))


if __name__ == "__main__":
    main()
