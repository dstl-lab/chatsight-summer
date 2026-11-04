"""Combine a saved review bundle with a Phase 3B ranking report."""
import argparse
import json
from pathlib import Path

from .findings.historical import private_json
from .fusion import FusionConfig, fuse_review_bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("ranking", type=Path)
    parser.add_argument("--mapping", type=Path,
                        help="JSON object mapping review session IDs to metric episode IDs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strong-score", type=float, default=50.0)
    parser.add_argument("--strong-tail-score", type=float, default=90.0)
    parser.add_argument("--strong-contributions", type=int, default=2)
    args = parser.parse_args(argv)
    mapping = json.loads(args.mapping.read_text()) if args.mapping else None
    if mapping is not None and not isinstance(mapping, dict):
        parser.error("--mapping must contain a JSON object")
    combined = fuse_review_bundle(
        json.loads(args.bundle.read_text()),
        json.loads(args.ranking.read_text()),
        session_episode_map=mapping,
        config=FusionConfig(args.strong_score, args.strong_tail_score,
                            args.strong_contributions),
    )
    private_json(args.output, combined)
    print(f"Wrote {len(combined['sessions'])} combined review sessions to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
