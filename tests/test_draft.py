from src.ingest.rawlog import Turn
from src.labeling.course import CourseProfile
from src.labeling.draft import (COVERAGE_PROMPT, SINGLE_LABEL_PROMPT,
                                CoverageVerdict, MessageLabels,
                                SingleLabelVerdict, _render_window,
                                classifier_hash, draft_labels)
from src.labeling.sampler import SampledMessage
from src.labeling.schema import LabelDef, LabelSchema

PROFILE = CourseProfile(
    course_name="Test 101", domain_description="a test course",
    tooling="pytest", paste_conventions="students paste tracebacks",
    reference_conventions="by number", message_shape_notes="short")

SCHEMA = LabelSchema(instructor_intent="i", labels=[
    LabelDef(name="asks-help", kind="behavioral", description="d",
             positive_criteria="p", negative_criteria="n")])

TWO_LABEL_SCHEMA = LabelSchema(instructor_intent="i", labels=[
    LabelDef(name="asks-help", kind="behavioral", description="asks for help",
             positive_criteria="p", negative_criteria="n"),
    LabelDef(name="frustrated", kind="behavioral", description="is frustrated",
             positive_criteria="p2", negative_criteria="n2")])


def _msg(**kw):
    base = dict(chatlog_id=1, conv_id="c", message_index=2, text="help 1.2",
                context=[Turn(index=0, role="student", text="earlier",
                              student_index=0),
                         Turn(index=1, role="tutor", text="reply")],
                context_after=None, stratum="s")
    base.update(kw)
    return SampledMessage(**base)


def _msg_i(i: int) -> SampledMessage:
    return SampledMessage(chatlog_id=100 + i, conv_id="c", message_index=i,
                          text=f"invented question {i}", context=[],
                          context_after="try a hint", stratum="short/early")


def make_fake(applies=True, no_label_fits=False, note=""):
    def gen(prompt, response_model):
        gen.calls.append((response_model.__name__, prompt))
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=applies, rationale="because")
        assert response_model is CoverageVerdict
        return CoverageVerdict(no_label_fits=no_label_fits, note=note)
    gen.calls = []
    return gen


def test_fanout_shape_one_call_per_label_plus_coverage():
    gen = make_fake()
    out = draft_labels([_msg_i(0), _msg_i(1)], TWO_LABEL_SCHEMA, PROFILE, gen)
    # (2 labels + 1 coverage) x 2 messages
    assert len(gen.calls) == 6
    single = [p for kind, p in gen.calls if kind == "SingleLabelVerdict"]
    coverage = [p for kind, p in gen.calls if kind == "CoverageVerdict"]
    assert len(single) == 4 and len(coverage) == 2
    # each single-label prompt carries exactly one label's criteria
    assert sum("p2" in p for p in single) == 2
    for p in single:
        assert ("asks-help" in p) != ("frustrated" in p)
    # coverage prompt sees every label name but no positive/negative criteria
    for p in coverage:
        assert "asks-help" in p and "frustrated" in p
    assert len(out) == 2
    assert out[0].labels == {"asks-help": True, "frustrated": True}
    assert out[0].rationales["asks-help"] == "because"


def test_coverage_note_lands_on_message_labels():
    gen = make_fake(applies=False, no_label_fits=True, note="asks about grades")
    out = draft_labels([_msg()], SCHEMA, PROFILE, gen)
    assert out[0].no_label_fits is True
    assert out[0].coverage_note == "asks about grades"
    assert out[0].labels == {"asks-help": False}


def test_coverage_call_runs_even_when_labels_apply():
    gen = make_fake(applies=True)
    draft_labels([_msg()], SCHEMA, PROFILE, gen)
    assert any(k == "CoverageVerdict" for k, _ in gen.calls)


def test_prompt_carries_course_context_and_window():
    gen = make_fake()
    draft_labels([_msg()], SCHEMA, PROFILE, gen)
    for _, p in gen.calls:
        assert "Test 101" in p
        assert "student: earlier" in p and "tutor: reply" in p
        assert p.index("student: earlier") < p.index("STUDENT MESSAGE TO LABEL")


def test_empty_rationale_defaults():
    def gen(prompt, response_model):
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="")
        return CoverageVerdict(no_label_fits=False)
    out = draft_labels([_msg()], SCHEMA, PROFILE, gen)
    assert out[0].rationales == {"asks-help": "(no rationale returned)"}


def test_message_labels_defaults_parse_old_snapshots():
    r = MessageLabels(chatlog_id=1, message_index=0, labels={},
                      rationales={})
    assert r.coverage_note == "" and r.no_label_fits is False


def test_on_result_fires_per_message_in_order():
    gen = make_fake()
    seen = []
    msgs = [_msg_i(0), _msg_i(1)]
    draft_labels(msgs, SCHEMA, PROFILE, gen,
                 on_result=lambda m, r: seen.append(m.message_index))
    assert seen == [0, 1]


def test_progress_counts_messages():
    gen = make_fake()
    ticks = []
    draft_labels([_msg_i(0), _msg_i(1)], SCHEMA, PROFILE, gen,
                 on_progress=lambda d, t: ticks.append((d, t)))
    assert ticks == [(1, 2), (2, 2)]


def test_render_window_empty():
    assert _render_window([]) == "(conversation start)"


def test_hash_covers_profile_window_schema_model():
    h = classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE)
    assert len(h) == 12
    assert h != classifier_hash(SCHEMA, "gemini-3.0", PROFILE)
    assert h != classifier_hash(TWO_LABEL_SCHEMA, "gemini-2.5-flash", PROFILE)
    assert h != classifier_hash(
        SCHEMA, "gemini-2.5-flash",
        PROFILE.model_copy(update={"tooling": "other"}))


def test_classifier_hash_golden_regression():
    # Golden literal pins BOTH templates, the profile rendering, and the
    # window rendering. Any intentional change to those must update this
    # literal — that update, and only that update, is the point of the test.
    h = classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE)
    assert h == "39dcf036b7d2"


import threading
import time


def test_calls_run_concurrently():
    barrier = threading.Barrier(3, timeout=5)

    def gen(prompt, response_model):
        barrier.wait()   # only passable with 3 calls truly in flight
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=False, rationale="r")
        return CoverageVerdict(no_label_fits=False)

    # 3 messages x (1 label + coverage) = 6 calls; barrier trips twice
    out = draft_labels([_msg_i(i) for i in range(3)], SCHEMA, PROFILE, gen,
                       workers=3)
    assert len(out) == 3


def test_output_order_despite_scrambled_completion():
    def gen(prompt, response_model):
        # later messages finish first
        for i in range(4):
            if f"invented question {i}" in prompt:
                time.sleep(0.05 * (3 - i))
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        return CoverageVerdict(no_label_fits=False)

    msgs = [_msg_i(i) for i in range(4)]
    seen = []
    ticks = []
    out = draft_labels(msgs, SCHEMA, PROFILE, gen, workers=4,
                       on_result=lambda m, r: seen.append(m.message_index),
                       on_progress=lambda d, t: ticks.append(d))
    assert [r.message_index for r in out] == [0, 1, 2, 3]
    assert sorted(seen) == [0, 1, 2, 3]        # any completion order
    assert ticks == [1, 2, 3, 4]               # strictly increasing


def test_failure_aborts_but_keeps_finished_messages():
    def gen(prompt, response_model):
        if "invented question 2" in prompt:
            raise RuntimeError("boom")
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        return CoverageVerdict(no_label_fits=False)

    msgs = [_msg_i(i) for i in range(3)]
    delivered = []
    try:
        draft_labels(msgs, SCHEMA, PROFILE, gen, workers=1,
                     on_result=lambda m, r: delivered.append(m.message_index))
        raise AssertionError("should have raised")
    except RuntimeError as e:
        assert str(e) == "boom"
    # workers=1 is sequential: messages 0 and 1 completed and were delivered,
    # message 2 failed, nothing after it ran
    assert delivered == [0, 1]


def test_workers_one_is_strictly_sequential():
    active = {"now": 0, "max": 0}
    lock = threading.Lock()

    def gen(prompt, response_model):
        with lock:
            active["now"] += 1
            active["max"] = max(active["max"], active["now"])
        time.sleep(0.005)
        with lock:
            active["now"] -= 1
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        return CoverageVerdict(no_label_fits=False)

    out = draft_labels([_msg_i(i) for i in range(3)], SCHEMA, PROFILE, gen,
                       workers=1)
    assert active["max"] == 1
    assert [r.message_index for r in out] == [0, 1, 2]
