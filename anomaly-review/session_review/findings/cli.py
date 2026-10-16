"""Prepare, analyze and export private review bundles. Importing UI data is offline."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from . import analyze_sessions as analyzer
from . import bundle, historical, runner, recent
from .contract import ReviewBundle


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Stream historical JSONL into a fixed offline pilot")
    prepare.add_argument("input", type=Path)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--count", type=int, default=20)
    prepare.add_argument("--seed", type=int, default=15)
    pr100 = sub.add_parser("prepare-recent", help="Use recent PR100 notebook actions and explicit request/execution bindings; no historical fallback")
    pr100.add_argument("input", type=Path)
    pr100.add_argument("--output", type=Path, required=True)
    pr100.add_argument("--count", type=int, default=5)
    pr100.add_argument("--seed", type=int, default=15)
    pr100.add_argument("--before-minutes", type=int, default=recent.BEFORE_MINUTES)
    pr100.add_argument("--after-minutes", type=int, default=recent.AFTER_MINUTES)
    pr100.add_argument("--coverage", choices=["rich", "dialogue"], default="rich")
    pr100.add_argument("--max-records", type=int, default=500)
    pr100.add_argument("--max-characters", type=int, default=160000)
    pr100.add_argument("--exclude-prepared", type=Path, action="append", default=[])
    export = sub.add_parser("export", help="Open prepared data/results offline as a UI bundle")
    analyze = sub.add_parser("analyze", help="One request per untouched session; requires --send")
    for command in (export, analyze):
        command.add_argument("prepared", type=Path)
        command.add_argument("--analysis", type=Path)
        command.add_argument("--model", default="gemini-3.8-flash")
        command.add_argument("--output", type=Path, required=True)
    analyze.add_argument("--send", action="store_true")
    demo = sub.add_parser("demo", help="Replay six input-pinned authored assessments offline")
    demo.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("check", help="Validate a saved UI bundle offline")
    check.add_argument("input", type=Path)
    schema = sub.add_parser("schema", help="Write the shared contract's JSON Schema")
    schema.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare-recent":
        manifest = recent.prepare(args.input, args.output, count=args.count, seed=args.seed,
            before_minutes=args.before_minutes, after_minutes=args.after_minutes, coverage=args.coverage,
            max_records=args.max_records, max_characters=args.max_characters, exclude_prepared=args.exclude_prepared)
        print(json.dumps({"selected_sessions": len(manifest["selected_session_ids"]), "eligible_sessions": manifest["eligible_notebook_sessions"], "exclusions": manifest["exclusions"], "quality": manifest["quality"]}))
        return 0
    if args.command == "prepare":
        manifest = historical.prepare(args.input, args.output, count=args.count, seed=args.seed)
        print(json.dumps({"selected_sessions": len(manifest["selected_session_ids"]), "quality": manifest["quality"],
            "eligible_conversations": manifest["eligible_conversations"], "conversation_exclusions": manifest["conversation_exclusions"]}))
        return 0
    if args.command == "schema":
        historical.private_json(args.output, ReviewBundle.model_json_schema())
        return 0
    if args.command == "check":
        doc = ReviewBundle.model_validate_json(args.input.read_bytes())
        print(f"Valid: {len(doc.sessions)} sessions. No model request.")
        return 0
    if args.output.exists() or args.output.is_symlink():
        parser.error("Output exists; choose a new file.")
    if args.command == "demo":
        fixtures = Path(__file__).resolve().parents[2] / "fixtures" / "findings"
        raw = (fixtures / "sessions.json").read_bytes()
        cache = json.loads((fixtures / "authored_assessments.json").read_text())
        if hashlib.sha256(raw).hexdigest() != cache["input_sha256"]:
            raise ValueError("Authored assessments do not match fixture bytes.")
        sessions = analyzer.Input.model_validate_json(raw).sessions
        evidence = [analyzer.assemble(s) for s in sessions]
        authored = {a["session_id"]: analyzer.Assessment.model_validate(a) for a in cache["assessments"]}
        results = {s.session_id: analyzer.validate_assessment(s, e, authored[s.session_id]) for s, e in zip(sessions, evidence)}
        data = bundle.build(sessions, input_hash=hashlib.sha256(raw).hexdigest(), results=results, source="authored offline assessments, not model inference")
    else:
        manifest, sessions, context, evidence = historical.load_prepared(args.prepared)
        analysis = args.analysis or args.prepared / "analysis"
        if args.command == "analyze":
            if not args.send:
                parser.error("--send is required. Prepared evidence, including any code/output records, will be sent to Gemini.")
            if not os.environ.get("GEMINI_API_KEY"):
                key = os.environ.get("GOOGLE_API_KEY")
                if not key:
                    parser.error("Set GEMINI_API_KEY or GOOGLE_API_KEY in the environment.")
                os.environ["GEMINI_API_KEY"] = key
            results = runner.run(analysis, sessions, evidence, model=args.model, send=True)
        else:
            results = runner.saved_results(analysis, sessions, evidence, args.model)
        data = bundle.build(sessions, input_hash=manifest["input_file_sha256"], context=context,
                            results=results, model=args.model if results else None,
                            source="saved Gemini assessments" if results else "not analyzed")
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    historical.private_json(args.output, data)
    print(json.dumps({"output": str(args.output), "sessions": len(data["sessions"]),
        "states": dict(__import__("collections").Counter(s["analysis"]["state"] for s in data["sessions"]))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
