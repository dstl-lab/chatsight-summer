"""Interactive draft->review->tweak loop. Drafting is anchored (instructor sees
model labels); this is fine for drafting and forbidden for measurement
(CLAUDE.md invariant 8)."""
import argparse
import subprocess
import sys
from typing import Callable

from src.config import Settings
from src.ingest.rawlog import Conversation, count_conversations, fetch_conversations
from src.labeling.course import DSC10_PROFILE, CourseProfile
from src.labeling.draft import draft_labels
from src.labeling.elicit import draft_schema, revise_schema
from src.labeling.llm import DEFAULT_MODEL, Generate, make_generate
from src.labeling.sampler import SampledMessage, stratified_sample
from src.labeling.schema import LabelSchema, save_schema
from src.labeling.snapshot import emit_snapshot

ACCEPT_NOTE = ("NOTE: acceptance is a drafting decision, not a reliability "
               "measurement (blind audit comes in Phase 0).")


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
             workers: int = 8) -> LabelSchema | None:
    schema = draft_schema(intent, profile, generate)
    sample = stratified_sample(conversations, n=sample_size, seed=seed)
    while True:
        labeled = draft_labels(sample, schema, profile, generate,
                               workers=workers)
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
    args = parser.parse_args()

    settings = Settings.load()
    if not settings.gemini_api_key:
        sys.exit("GEMINI_API_KEY missing from .env")
    workers = args.workers or settings.labeling_workers
    generate = make_generate(settings.gemini_api_key)

    intent = args.intent or input(
        "What trends do you want to see in the chat data "
        "(conceptual, behavioral, ...)? ")

    print(f"Fetching up to {args.max_conversations} conversations "
          "(is bin/tunnel running?)...")
    conversations = fetch_conversations(settings.ext_db_url,
                                        limit=args.max_conversations)
    total_conversations = count_conversations(settings.ext_db_url)
    excluded_conversations = max(0, total_conversations - len(conversations))
    print(f"Fetched {len(conversations)} conversations. DB holds "
          f"{total_conversations} total; {excluded_conversations} are "
          f"EXCLUDED from this run and the snapshot "
          f"(--max-conversations={args.max_conversations}).")

    schema = run_loop(intent, conversations, generate,
                      profile=DSC10_PROFILE,
                      sample_size=args.sample_size, seed=args.seed,
                      ask=input, say=print, workers=workers)
    if schema is None:
        print("Quit without accepting; nothing written.")
        return

    save_schema(schema, settings.data_dir)
    print(f"Accepted schema {schema.version_id}. Mass-labeling "
          f"{len(conversations)} conversations...")
    all_messages = stratified_sample(conversations, n=10**9, seed=args.seed)
    labeled = draft_labels(all_messages, schema, DSC10_PROFILE, generate,
                           workers=workers)
    abstained = sum(1 for r in labeled if r.no_label_fits)
    if labeled:
        print(f"Coverage: {abstained} of {len(labeled)} messages "
              f"({abstained / len(labeled):.0%}) showed acts no label "
              f"captures.")
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
                         profile=DSC10_PROFILE)
    print(f"Snapshot written: {path}")
    print("Add a row to snapshots.md with this manifest's provenance.")


if __name__ == "__main__":
    main()
