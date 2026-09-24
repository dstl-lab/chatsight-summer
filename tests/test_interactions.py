from datetime import timedelta

from src.episodes.models import EpisodeEvent
from src.episodes.reconstruct import reconstruct_episodes
from src.viewer.insights import build_journeys
from src.viewer.interactions import build_exchanges, build_progressions
from tests.test_episode_viewer import event, BASE


def journey(rows):
    return build_journeys(reconstruct_episodes([EpisodeEvent.model_validate(row) for row in rows]))[0]


def test_every_exchange_retains_context_across_pass_and_time_gap():
    record = journey([
        event(1, "cell_error", {"error_name": "ValueError"}),
        event(2, "tutor_query", {}, turn_id="one"),
        event(3, "tutor_response", {}, turn_id="one", response_id="r1"),
        event(4, "cell_edit", {"characters_inserted": 2, "characters_deleted": 0}),
        event(5, "autograder_completed", {"success": True}),
        event(6, "tutor_query", {"request_origin": "accepted-suggestion", "mode": "tutor"}, turn_id="two", occurred_at=(BASE + timedelta(hours=2)).isoformat()),
        event(7, "tutor_response", {}, turn_id="two", response_id="r2", occurred_at=(BASE + timedelta(hours=2, seconds=2)).isoformat()),
    ])
    exchanges = build_exchanges(record)
    assert len(record.episodes) > 1
    assert len(exchanges) == 2
    assert exchanges[0]["context"] == "After an error or failed check"
    assert exchanges[0]["after_ids"] == ["viewer-event-4", "viewer-event-5"]
    assert exchanges[1]["context"] == "After a passing check"
    assert exchanges[1]["request_origin"] == "Accepted tutor suggestion"
    assert exchanges[1]["tutor_mode"] == "Guided tutor"
    assert exchanges[1]["earlier_context_ids"] == [f"viewer-event-{n}" for n in range(1, 6)]
    group = build_progressions([record])[0]
    assert group["student_count"] == 1
    assert group["exchange_count"] == 2
    assert len(group["exchange_steps"]) == 2


def test_reply_and_transfer_require_matching_identifiers():
    record = journey([
        event(1, "tutor_query", {}, turn_id="one"),
        event(2, "tutor_response", {}, turn_id="other", response_id="old"),
        event(3, "tutor_response", {"code_block_count": 1}, turn_id="one", response_id="right"),
        event(4, "notebook_paste", {"provenance": "copied_then_pasted", "matched_response_id": "old"}, response_id="old"),
        event(5, "tutor_code_inserted", {}, response_id="right"),
    ])
    exchange = build_exchanges(record)[0]
    assert exchange["reply_id"] == "viewer-event-3"
    assert exchange["linked_transfer_ids"] == ["viewer-event-5"]
    assert "link to this reply unknown" in exchange["outcome"]


def test_missing_and_ambiguous_replies_do_not_borrow_another_turn():
    record = journey([
        event(1, "tutor_query", {}, turn_id="one"),
        event(2, "cell_edit", {}),
        event(3, "tutor_query", {}, turn_id="two"),
        event(4, "tutor_response", {}, turn_id="two"),
        event(5, "tutor_response", {}, turn_id="two"),
    ])
    exchanges = build_exchanges(record)
    assert all(e["reply_id"] is None for e in exchanges)
    assert exchanges[0]["during_ids"] == ["viewer-event-2"]
    assert exchanges[0]["after_ids"] == []
    assert all(e["request_origin"] == "Not recorded" for e in exchanges)


def test_late_reply_does_not_claim_later_turn_actions():
    record = journey([
        event(1, "tutor_query", {}, turn_id="one"),
        event(2, "tutor_query", {}, turn_id="two"),
        event(3, "tutor_response", {}, turn_id="one"),
        event(4, "cell_edit", {}),
    ])
    first = build_exchanges(record)[0]
    assert first["reply_id"] == "viewer-event-3"
    assert first["after_ids"] == []
    assert first["outcome"] == "Reply arrived after the next request"


def test_demo_category_requires_explicit_synthetic_marker():
    for marked in (True, False):
        record = journey([event(1, "tutor_query", {
            "synthetic_message_act": "direct-request",
            "synthetic_ground_truth": marked,
        })])
        result = build_exchanges(record)[0]
        assert result["demo_request_label"] == ("Request an answer" if marked else None)


def test_legacy_order_match_only_when_both_turn_ids_absent():
    record = journey([
        event(1, "tutor_query", {}, turn_id=None),
        event(2, "tutor_response", {}, turn_id=None),
    ])
    assert build_exchanges(record)[0]["reply_link"] == "recorded-order"
