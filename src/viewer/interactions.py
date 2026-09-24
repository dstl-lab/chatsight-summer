"""Inspectable request-anchored exchanges and whole-question progressions.

Intervals describe recorded order, never causation or a student's mental state.
Matching identifiers outrank adjacency; missing or ambiguous replies stay unknown.
"""

from collections import defaultdict

from src.viewer.insights import sequence_context_at

CONTEXT = {
    "before-attempt": "No earlier edit or run recorded",
    "after-attempt": "After an edit or run",
    "after-problem": "After an error or failed check",
    "after-pass": "After a passing check",
}
DEMO_REQUESTS = {
    "validation": "Check an answer",
    "debugging-request": "Help with an error",
    "conceptual-clarification": "Explain a concept",
    "syntax-help": "Help with syntax",
    "direct-request": "Request an answer",
    "assignment-reference": "Clarify the question",
}
ORIGINS = {
    "student-written": "Student-written",
    "accepted-suggestion": "Accepted tutor suggestion",
    "edited-suggestion": "Edited tutor suggestion",
}


def build_exchanges(journey):
    events = journey.events
    queries = [i for i, event in enumerate(events) if event.event_type == "tutor_query"]
    exchanges = []
    for number, index in enumerate(queries):
        query = events[index]
        stop = queries[number + 1] if number + 1 < len(queries) else len(events)
        candidates = [
            i for i in range(index + 1, len(events))
            if events[i].event_type == "tutor_response"
            and (not query.conversation_id or not events[i].conversation_id
                 or query.conversation_id == events[i].conversation_id)
            and (
                (query.turn_id and query.turn_id == events[i].turn_id)
                or (not query.turn_id and not events[i].turn_id and i < stop)
            )
        ]
        # Reused IDs are ambiguous: do not silently select the first reply.
        reply_index = candidates[0] if len(candidates) == 1 else None
        reply = events[reply_index] if reply_index is not None else None
        after = events[reply_index + 1:stop] if reply_index is not None and reply_index < stop else []
        actions = [e for e in after if e.event_type not in {"tutor_query", "tutor_response"}]
        transfers = [e for e in actions if reply and reply.response_id and (
            (e.event_type == "tutor_code_inserted" and e.response_id == reply.response_id)
            or (e.event_type == "notebook_paste"
                and e.payload.get("matched_response_id") == reply.response_id
                and e.payload.get("provenance") == "copied_then_pasted")
        )]
        steps = []
        for event in actions:
            label = None
            if event in transfers:
                label = "Linked tutor code inserted or pasted"
            elif event.event_type == "cell_edit":
                label = "Notebook edited"
            elif event.event_type == "notebook_paste":
                label = "Content pasted; link to this reply unknown"
            elif event.event_type == "tutor_code_inserted":
                label = "Tutor code inserted; link to this reply unknown"
            elif event.event_type == "cell_execution_started" and not event.payload.get("is_autograder"):
                label = "Code run"
            elif event.event_type == "cell_error":
                label = "Execution error"
            elif event.event_type == "autograder_completed":
                success = event.payload.get("success")
                label = "Check passed" if success is True else "Check failed" if success is False else "Check result unknown"
            if label and (not steps or steps[-1] != label):
                steps.append(label)
        context = CONTEXT[sequence_context_at(events, index)]
        if reply is None:
            outcome = "Reply not linked"
        elif reply_index >= stop:
            outcome = "Reply arrived after the next request"
        else:
            outcome = " → ".join(steps) or "No later notebook action recorded"
        origin = ORIGINS.get(query.payload.get("request_origin"), "Not recorded")
        mode = query.payload.get("tutor_mode") or query.payload.get("mode")
        mode = {"tutor": "Guided tutor", "chatgpt": "General assistant"}.get(mode, "Not recorded")
        demo = DEMO_REQUESTS.get(query.payload.get("synthetic_message_act")) if query.payload.get("synthetic_ground_truth") is True else None
        exchanges.append({
            "number": number + 1,
            "query_id": query.event_id,
            "reply_id": reply.event_id if reply else None,
            "reply_link": "turn-id" if reply and query.turn_id else "recorded-order" if reply else "unavailable",
            "context": context,
            "request_origin": origin,
            "tutor_mode": mode,
            "demo_request_label": demo,
            "before_ids": [e.event_id for e in events[(queries[number - 1] + 1 if number else 0):index] if e.event_type not in {"tutor_query", "tutor_response"}],
            "earlier_context_ids": [e.event_id for e in events[:index]],
            "after_ids": [e.event_id for e in actions],
            "during_ids": [e.event_id for e in events[index + 1:min(reply_index if reply_index is not None else stop, stop)] if e.event_type not in {"tutor_query", "tutor_response"}],
            "linked_transfer_ids": [e.event_id for e in transfers],
            "outcome": outcome,
            "steps": steps,
            "reply_has_code": bool(reply and reply.payload.get("code_block_count", 0)),
            "window_end": "next-request" if stop < len(events) else "end-of-record",
        })
    return exchanges


def build_progressions(journeys):
    groups = defaultdict(list)
    for journey in journeys:
        if not journey.tutor_used:
            continue
        exchanges = build_exchanges(journey)
        signature = tuple(
            f"{e['context']} → {'Tutor reply with code' if e['reply_has_code'] else 'Tutor reply' if e['reply_id'] else 'Request'} → {e['outcome']}"
            for e in exchanges
        )
        groups[signature].append(journey)
    result = []
    for index, (signature, members) in enumerate(sorted(groups.items())):
        result.append({
            "id": f"progression-{index}",
            "title": " / Next exchange: ".join(signature),
            "exchange_steps": list(signature),
            "student_count": len({m.student_key for m in members}),
            "interaction_count": len(members),
            "exchange_count": sum(m.tutor_turn_count for m in members),
            "journey_ids": [m.journey_id for m in members],
            "event_ids": [e.event_id for m in members for e in m.events if e.event_type == "tutor_query"],
        })
    return sorted(result, key=lambda row: (-row["student_count"], row["title"]))
