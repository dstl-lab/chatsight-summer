"""Isolated optimized sweep commands. Preparation/reporting/export never call Gemini."""
import argparse
import json
import os
import time
from pathlib import Path

from . import bulk, bundle, grouped, historical as h, native_batch, optimized, provider, runner


def prepared_paths(root):
    root = Path(root)
    if (root / "sessions.json").exists(): return [root]
    metadata = root / "sweep.private.json"
    if metadata.exists():
        doc = json.loads(metadata.read_text())
        return [root / "batches" / b["folder"] for b in doc["preparation"]["batches"]]
    raise ValueError("Choose a prepared batch or an optimized sweep directory")


def options_from_prepared(prepared):
    plan = json.loads((Path(prepared) / "analysis-optimized/plan.json").read_text())
    settings = plan["inference"]
    return provider.Options(compact=settings["compact"], thinking=settings["thinking"], max_output_tokens=settings["max_output_tokens"])


def inspect(paths, options, limit=50):
    count = original = sent = estimate = total = 0
    for path in paths:
        if count >= limit:
            total += len(json.loads((Path(path) / "manifest.json").read_text())["selected_session_ids"])
            continue
        _, sessions, _, evidence = h.load_prepared(path)
        total += len(sessions)
        for item in evidence:
            if count >= limit: continue
            _, _, metrics = provider.payload(item, options)
            original += metrics["original_characters"]; sent += metrics["sent_characters"]; estimate += metrics["estimated_tokens"]; count += 1
    return {"total_units": total, "sampled_units": count, "original_characters": original, "sent_characters": sent,
        "character_reduction_percent": round(100 * (1 - sent / original), 2) if original else None,
        "mean_estimated_reserved_tokens": estimate / count if count else None,
        "token_estimates_are_not_provider_measurements": True, "model_calls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("input", type=Path)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--group-overlap", action="store_true")
    prepare.add_argument("--minutes", type=int, choices=[10,25], default=25)
    prepare.add_argument("--group-gap", type=int, default=10)
    prepare.add_argument("--max-span", type=int, default=60)
    for name in ("run", "inspect", "report", "batch-prepare"):
        command = sub.add_parser(name)
        command.add_argument("prepared", type=Path)
        if name != "report":
            command.add_argument("--model", default="gemini-3.8-flash")
            command.add_argument("--workers", type=int, default=4)
            command.add_argument("--rpm", type=int, default=30)
            command.add_argument("--tpm", type=int, default=200000)
            command.add_argument("--original-prompt", action="store_true")
            command.add_argument("--thinking", choices=["default","low","medium","high"], default="default")
            command.add_argument("--max-output-tokens", type=int, default=8192)
            command.add_argument("--max-requests", type=int, default=0)
            command.add_argument("--max-estimated-tokens", type=int, default=0)
        if name == "run": command.add_argument("--send", action="store_true")
        if name == "batch-prepare":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--enqueued-tokens", type=int, required=True, help="Operator's configured native batch token allowance")
    for name in ("batch-submit", "batch-collect", "batch-watch", "batch-attach"):
        command = sub.add_parser(name); command.add_argument("batch", type=Path)
        if name in {"batch-submit", "batch-watch"}: command.add_argument("--send", action="store_true")
        if name == "batch-attach":
            command.add_argument("--chunk", type=int, required=True); command.add_argument("--remote-name", required=True)
    export = sub.add_parser("export")
    export.add_argument("prepared", type=Path); export.add_argument("--model", default="gemini-3.8-flash"); export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        if args.command == "prepare":
            if args.output.exists(): raise FileExistsError(args.output)
            args.output.mkdir(parents=True, mode=0o700)
            index = args.output / "events.sqlite"
            source = bulk.index_source(args.input, index)
            function = grouped.prepare_batches if args.group_overlap else bulk.prepare_batches
            kwargs = {"gap_minutes": args.group_gap, "max_span_minutes": args.max_span} if args.group_overlap else {}
            result = function(index, args.output / "batches", source, minutes=args.minutes, **kwargs)
            h.private_json(args.output / "sweep.private.json", {"format": "pr100.optimized-sweep.v1", "source": source, "preparation": result})
            print(json.dumps({"coverage": result["coverage"], "batches": len(result["batches"]), "model_calls": 0}))
            return 0
        if args.command in {"batch-submit", "batch-collect", "batch-watch", "batch-attach"}:
            state = native_batch.read(args.batch)
            inference = state["inference"]
            options = provider.Options(transport="batch", compact=inference["compact"], thinking=inference["thinking"], max_output_tokens=inference["max_output_tokens"])
            if args.command == "batch-attach":
                native_batch.attach(args.batch, chunk_number=args.chunk, remote_name=args.remote_name)
                print("Remote job attached; no new provider request."); return 0
            if args.command in {"batch-submit", "batch-watch"} and not args.send: parser.error("--send is required")
            api = provider.client(options)
            try:
                if args.command == "batch-watch":
                    while True:
                        native_batch.submit(args.batch, options=options, api=api, send=True)
                        result = native_batch.collect(args.batch, options=options, api=api)
                        print(json.dumps({k: result.get(k) for k in ("provider_status", "completed", "failed", "pending")}), flush=True)
                        if result["provider_status"] == "completed": break
                        time.sleep(15)
                else:
                    result = native_batch.submit(args.batch, options=options, api=api, send=args.send) if args.command == "batch-submit" else native_batch.collect(args.batch, options=options, api=api)
            finally: api.close()
            print(json.dumps({k: result.get(k) for k in ("status", "provider_status", "requests", "completed", "failed", "pending")})); return 0
        paths = prepared_paths(args.prepared)
        if args.command == "report":
            print(json.dumps(optimized.statistics(paths))); return 0
        if args.command == "export":
            if len(paths) != 1: raise ValueError("Export one review batch at a time")
            path = paths[0]; manifest, sessions, contexts, _ = h.load_prepared(path)
            options = options_from_prepared(path)
            results = optimized.saved_results(path, args.model, options)
            doc = bundle.build(sessions, input_hash=manifest["input_file_sha256"], context=contexts, results=results, model=args.model,
                source="Saved optimized assessments; original evidence retained")
            h.private_json(args.output, doc); print("Review bundle saved; no model call."); return 0
        options = provider.Options(workers=args.workers, rpm=args.rpm, tpm=args.tpm, compact=not args.original_prompt,
            thinking=args.thinking, max_output_tokens=args.max_output_tokens, max_requests=args.max_requests,
            max_estimated_tokens=args.max_estimated_tokens, transport="batch" if args.command == "batch-prepare" else "concurrent",
            batch_enqueued_tokens=args.enqueued_tokens if args.command == "batch-prepare" else 0)
        if args.command == "inspect":
            print(json.dumps(inspect(paths, options))); return 0
        cache = args.prepared.parent / "optimized-assessment-cache"
        if args.command == "batch-prepare":
            result = native_batch.prepare(paths, args.output, model=args.model, options=options, cache_folder=cache)
            print(json.dumps({"requests": result["requests"], "estimated_tokens": result["estimated_tokens"], "chunks": len(result["chunks"]), "model_calls": 0})); return 0
        result = optimized.run_many(paths, model=args.model, options=options, send=args.send, cache_folder=cache)
        runner.atomic_json(args.prepared / "optimized-report.private.json", result)
        print(json.dumps(result)); return 0
    except Exception as error:
        # Arbitrary provider diagnostics may echo prompts or credentials.
        print(json.dumps({"error_type": type(error).__name__, "message": "Command stopped. Saved inputs, receipts and remote job identities are preserved; no automatic resubmission."}))
        return 1


if __name__ == "__main__": raise SystemExit(main())
