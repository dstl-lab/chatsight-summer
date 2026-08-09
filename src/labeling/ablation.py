"""Context-ablation probe (2026-08-07): relabel messages with the
conversation window, tutor-after, and latency stripped, and measure which
labels' verdicts change. A label whose verdicts never differ is
context-inert — it judges surface text, whatever the prompt offers it. This
is a *sensitivity* diagnostic, not an accuracy measure: flips say the
context is load-bearing, only blind audit says who is right (invariant 1).
Reads a snapshot, re-runs the classifier ablated, writes nothing to the
snapshot (rule 3: snapshots are immutable)."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from src.ingest.rawlog import Conversation
from src.labeling.draft import MessageLabels, draft_labels
from src.labeling.sampler import SampledMessage, stratified_sample
from src.labeling.schema import LabelSchema


def strip_context(m: SampledMessage) -> SampledMessage:
    return m.model_copy(update={
        "context": [], "context_after": None,
        "latency_seconds": None, "latency_bucket": "unknown"})


def flip_stats(original: list[MessageLabels], ablated: list[MessageLabels]
               ) -> dict:
    by_key = {(r.chatlog_id, r.message_index): r for r in original}
    per_label: Counter = Counter()
    per_label_total: Counter = Counter()
    flipped_messages = 0
    for a in ablated:
        o = by_key[(a.chatlog_id, a.message_index)]
        message_flipped = False
        for name, ov in o.labels.items():
            per_label_total[name] += 1
            if bool(a.labels.get(name)) != bool(ov):
                per_label[name] += 1
                message_flipped = True
        flipped_messages += message_flipped
    return {"messages": len(ablated), "messages_with_flips": flipped_messages,
            "per_label": {n: {"flips": per_label[n],
                              "total": per_label_total[n]}
                          for n in sorted(per_label_total)}}


def render_report(stats: dict) -> str:
    lines = [f"Context-ablation probe: {stats['messages_with_flips']} of "
             f"{stats['messages']} messages changed at least one verdict "
             "without context."]
    inert = []
    for name, s in sorted(stats["per_label"].items(),
                          key=lambda kv: -kv[1]["flips"]):
        rate = s["flips"] / s["total"] if s["total"] else 0
        lines.append(f"  {name:<34}{s['flips']:>3}/{s['total']} flips "
                     f"({rate:.0%})")
        if s["flips"] == 0:
            inert.append(name)
    if inert:
        lines.append("  CONTEXT-INERT (0 flips — verdicts ignore context "
                     "on this sample): " + ", ".join(inert))
    return "\n".join(lines)


def main() -> None:
    from src.config import Settings
    from src.labeling.llm import make_generate
    from src.labeling.profile2 import load_profile

    parser = argparse.ArgumentParser(description="Context-ablation probe")
    parser.add_argument("snapshot_dir")
    parser.add_argument("--sample", type=int, default=25)
    parser.add_argument("--seed", type=int, default=0,
                        help="seed the snapshot's mass pass used")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    settings = Settings.load()
    if not settings.gemini_api_key:
        sys.exit("GEMINI_API_KEY missing from .env")
    snap = Path(args.snapshot_dir)
    conversations = [Conversation.model_validate_json(l)
                     for l in (snap / "conversations.jsonl").open()]
    schema = LabelSchema.model_validate_json((snap / "schema.json").read_text())
    original = [MessageLabels.model_validate_json(l)
                for l in (snap / "labels.jsonl").open()]
    manifest = json.loads((snap / "manifest.json").read_text())
    profile2 = load_profile(args.profile) if args.profile else None
    if (profile2.profile_id if profile2 else None) != manifest.get("profile2_id"):
        sys.exit("--profile does not match the snapshot's profile2_id — the "
                 "probe must re-run the exact classifier (rule 2)")

    messages = stratified_sample(conversations, n=10**9, seed=args.seed)
    keys = {(r.chatlog_id, r.message_index) for r in original}
    messages = [m for m in messages
                if (m.chatlog_id, m.message_index) in keys][:args.sample]
    generate = make_generate(settings.gemini_api_key)
    workers = (args.workers if args.workers is not None
               else settings.labeling_workers)
    ablated = draft_labels([strip_context(m) for m in messages], schema,
                           settings_profile(manifest), generate,
                           workers=workers, profile2=profile2)
    print(render_report(flip_stats(
        [r for r in original
         if (r.chatlog_id, r.message_index) in
         {(m.chatlog_id, m.message_index) for m in messages}], ablated)))


def settings_profile(manifest: dict):
    from src.labeling.course import CourseProfile
    return CourseProfile.model_validate(manifest["course_profile"])


if __name__ == "__main__":
    main()
