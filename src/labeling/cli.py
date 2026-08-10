"""Interactive draft->review->tweak loop. Drafting is anchored (instructor sees
model labels); this is fine for drafting and forbidden for measurement
(CLAUDE.md invariant 8)."""
import argparse
import subprocess
import sys
from typing import Callable

from src.config import Settings
from src.ingest.rawlog import Conversation, count_conversations, fetch_conversations
from src.ingest.sequences import (BEFORE_MIN, OUTCOME_MIN,
                                  fetch_autograder_runs, fetch_traceback_flags)
from src.labeling.course import DSC10_PROFILE, CourseProfile
from src.labeling.draft import draft_labels
from src.labeling.elicit import draft_schema, revise_schema
from src.labeling.llm import DEFAULT_MODEL, Generate, make_generate
from src.labeling.sampler import SampledMessage, stratified_sample
from src.labeling.schema import LabelSchema, save_schema
from src.labeling.snapshot import emit_snapshot

ACCEPT_NOTE = ("NOTE: acceptance is a drafting decision, not a reliability "
               "measurement (blind audit comes in Phase 0).")


def load_accepted_profile(path: str):
    """Load a CourseProfile v2 artifact, refusing drafts: the accept gate is
    git review of the artifact (2026-08-07 memo), so an accepted:false file
    reaching the classify path means review was skipped."""
    from src.labeling.profile2 import load_profile
    v2 = load_profile(path)
    if not v2.accepted:
        sys.exit(f"profile {path} has accepted: false — review the draft, "
                 "set accepted:true, rename per the explore CLI's "
                 "instructions, and commit it first.")
    return v2


def _render(schema: LabelSchema, sample: list[SampledMessage],
            labeled, say: Callable[[str], None]) -> None:
    say(f"\n=== Schema {schema.version_id} ===")
    for l in schema.labels:
        say(f"  {l.name} ({l.kind}): {l.description}")
    by_key = {(r.chatlog_id, r.message_index): r for r in labeled}
    say(f"\n=== Sample ({len(sample)} messages) ===")
    for m in sample:
        r = by_key.get((m.chatlog_id, m.message_index))
        applied = [k for k, v in r.labels.items() if v] if r else []
        say(f"\n[{m.stratum}] {m.text}")
        say(f"  -> {', '.join(applied) if applied else '(no labels)'}")
        if r:
            for k in applied:
                say(f"     {k}: {r.rationales.get(k, '')}")


def run_loop(intent: str, conversations: list[Conversation], generate: Generate,
             *, profile: CourseProfile, sample_size: int, seed: int,
             ask: Callable[[str], str],
             say: Callable[[str], None],
             workers: int = 8, profile2=None, runs=None,
             traceback_flags=None) -> LabelSchema | None:
    schema = draft_schema(intent, profile, generate, profile2=profile2)
    sample = stratified_sample(conversations, n=sample_size, seed=seed,
                               runs=runs, traceback_flags=traceback_flags)
    while True:
        labeled = draft_labels(sample, schema, profile, generate,
                               workers=workers, profile2=profile2)
        _render(schema, sample, labeled, say)
        say(f"\n{ACCEPT_NOTE}")
        choice = ask("accept/tweak/quit> ").strip().lower()
        if choice == "accept":
            return schema
        if choice == "quit":
            return None
        if choice == "tweak":
            feedback = ask("what should change? ")
            schema = revise_schema(schema, feedback, profile, generate)


def main() -> None:
    parser = argparse.ArgumentParser(description="Top-down labeling loop")
    parser.add_argument("--intent")
    parser.add_argument("--max-conversations", type=int, default=200)
    parser.add_argument("--sample-size", type=int, default=25)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--workers", type=int, default=None,
                        help="parallel Gemini calls (default: "
                             "LABELING_WORKERS or 8)")
    parser.add_argument("--profile", default=None,
                        help="accepted CourseProfile v2 artifact "
                             "(profiles/<slug>.json) to ground this run")
    parser.add_argument("--no-sequence", action="store_true",
                        help="skip the autograder-run/traceback sequence-"
                             "context fetch (needed when the events table "
                             "lacks autograder rows)")
    parser.add_argument("--since", default=None,
                        help="ISO date: only conversations starting on/after "
                             "this date (requires --until)")
    parser.add_argument("--until", default=None,
                        help="ISO date, exclusive upper bound "
                             "(requires --since)")
    args = parser.parse_args()
    sequence = not args.no_sequence

    settings = Settings.load()
    if not settings.gemini_api_key:
        sys.exit("GEMINI_API_KEY missing from .env")
    workers = (args.workers if args.workers is not None
              else settings.labeling_workers)
    profile2 = load_accepted_profile(args.profile) if args.profile else None
    generate = make_generate(settings.gemini_api_key)

    intent = args.intent or input(
        "What trends do you want to see in the chat data "
        "(conceptual, behavioral, ...)? ")

    print(f"Fetching up to {args.max_conversations} conversations "
          "(is bin/tunnel running?)...")
    conversations = fetch_conversations(settings.ext_db_url,
                                        limit=args.max_conversations,
                                        since=args.since, until=args.until)
    total_conversations = count_conversations(settings.ext_db_url)
    excluded_conversations = max(0, total_conversations - len(conversations))
    print(f"Fetched {len(conversations)} conversations. DB holds "
          f"{total_conversations} total; {excluded_conversations} are "
          f"EXCLUDED from this run and the snapshot "
          f"(--max-conversations={args.max_conversations}).")

    runs = fetch_autograder_runs(settings.ext_db_url, conversations) \
        if sequence else None
    traceback_flags = fetch_traceback_flags(settings.ext_db_url, conversations) \
        if sequence else None

    schema = run_loop(intent, conversations, generate,
                      profile=DSC10_PROFILE,
                      sample_size=args.sample_size, seed=args.seed,
                      ask=input, say=print, workers=workers,
                      profile2=profile2, runs=runs,
                      traceback_flags=traceback_flags)
    if schema is None:
        print("Quit without accepting; nothing written.")
        return

    save_schema(schema, settings.data_dir)
    if profile2 is not None:
        # Layered composition (2026-08-07 memo): promoted concepts and
        # accepted affect/intent layers join the accepted instructor schema
        # for the mass pass; chains parent_version (invariant 6).
        from src.labeling.profile2 import compose_schema
        schema = compose_schema(profile2, schema)
        save_schema(schema, settings.data_dir)
        print(f"Composed with profile {profile2.profile_id}: "
              f"schema {schema.version_id} ({len(schema.labels)} labels)")
    print(f"Accepted schema {schema.version_id}. Mass-labeling "
          f"{len(conversations)} conversations...")
    all_messages = stratified_sample(conversations, n=10**9, seed=args.seed,
                                     runs=runs, traceback_flags=traceback_flags)
    labeled = draft_labels(all_messages, schema, DSC10_PROFILE, generate,
                           workers=workers, profile2=profile2)
    abstained = sum(1 for r in labeled if r.no_label_fits)
    if labeled:
        print(f"Coverage: {abstained} of {len(labeled)} messages "
              f"({abstained / len(labeled):.0%}) showed acts no label "
              f"captures.")
        from src.labeling.distinctness import distinctness_report
        print(distinctness_report(labeled))
    try:
        repo_sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                  capture_output=True, text=True,
                                  cwd=settings.repo_root).stdout.strip()
    except OSError:
        repo_sha = ""
    if not repo_sha:
        print("WARNING: could not determine repo_sha from git; "
              "recording 'unknown' in the manifest.")
        repo_sha = "unknown"
    path = emit_snapshot(conversations, labeled, schema, model=DEFAULT_MODEL,
                         repo_sha=repo_sha, data_dir=settings.data_dir,
                         excluded_conversations=excluded_conversations,
                         profile=DSC10_PROFILE, profile2=profile2,
                         sequence_context={"before_min": BEFORE_MIN,
                                           "outcome_min": OUTCOME_MIN,
                                           "enabled": sequence})
    print(f"Snapshot written: {path}")
    print("Add a row to snapshots.md with this manifest's provenance.")


if __name__ == "__main__":
    main()
