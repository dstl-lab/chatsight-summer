"""Offline, create-only file processing. No database, execution, or model calls."""
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .normalize import load_json
from .sessions import SessionConfig, reconstruct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gap-seconds", type=int, default=1800)
    args = parser.parse_args()
    try:
        result = reconstruct(load_json(args.input.read_bytes()), SessionConfig(args.gap_seconds))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            json.dump(result, file, indent=2, ensure_ascii=True, allow_nan=False)
            file.write("\n")
    except ValidationError:
        parser.exit(2, "Invalid input envelope; expected anomaly-review.canonical.v1.\n")
    except (OSError, ValueError):
        parser.exit(2, "Cannot process input or create output; verify format, paths, and gap. Existing output is never overwritten.\n")
    print(json.dumps({"origin": result["origin"], "episodes": len(result["episodes"]),
                      "unassigned_events": len(result["unassigned"]),
                      "rejected_records": len(result["normalization"]["rejected"])}))
    if result["normalization"]["rejected"]:
        parser.exit(1, "Report saved with rejected records; inspect diagnostics before analysis.\n")


if __name__ == "__main__":
    main()
