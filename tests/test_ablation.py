from src.ingest.rawlog import Turn
from src.labeling.ablation import flip_stats, render_report, strip_context
from src.labeling.draft import MessageLabels
from src.labeling.sampler import SampledMessage


def _msg(**kwargs):
    defaults = dict(
        chatlog_id=1, conv_id="c", message_index=2, text="1.6",
        context=[Turn(index=0, role="student", text="earlier",
                      student_index=0),
                 Turn(index=1, role="tutor", text="reply")],
        context_after="after", stratum="s",
        latency_seconds=42.0, latency_bucket="rapid",
        pre_pattern="", last_run_minutes=None, last_run_grader="",
        last_run_success=None, snapshot_traceback=False, mode="",
        seq_granularity="")
    defaults.update(kwargs)
    return SampledMessage(**defaults)


def _labels(i, **labels):
    return MessageLabels(chatlog_id=1, message_index=i, labels=labels,
                         rationales={k: "r" for k in labels})


def test_strip_context_removes_all_context_channels():
    s = strip_context(_msg())
    assert s.context == [] and s.context_after is None
    assert s.latency_seconds is None and s.latency_bucket == "unknown"
    assert s.text == "1.6"          # the message itself is untouched


def test_flip_stats_and_report():
    original = [_labels(0, deictic=True, surface=True),
                _labels(1, deictic=True, surface=False)]
    ablated = [_labels(0, deictic=False, surface=True),   # deictic flipped
               _labels(1, deictic=False, surface=False)]  # deictic flipped
    stats = flip_stats(original, ablated)
    assert stats["messages"] == 2
    assert stats["messages_with_flips"] == 2
    assert stats["per_label"]["deictic"] == {"flips": 2, "total": 2}
    assert stats["per_label"]["surface"] == {"flips": 0, "total": 2}
    rep = render_report(stats)
    assert "2 of 2 messages" in rep
    assert "deictic" in rep and "100%" in rep
    assert "CONTEXT-INERT" in rep and "surface" in rep


def test_strip_sequence_resets_only_sequence_fields():
    from src.labeling.ablation import strip_sequence
    m = _msg(pre_pattern="fail-then-ask", last_run_success=False,
             snapshot_traceback=True, mode="chatgpt",
             latency_seconds=30.0, latency_bucket="rapid")
    s = strip_sequence(m)
    assert s.pre_pattern == "" and s.last_run_success is None
    assert s.mode == "" and not s.snapshot_traceback
    assert s.latency_bucket == "rapid"        # latency axis untouched
    assert s.context == m.context             # structural context untouched
