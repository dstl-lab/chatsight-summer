import threading
import time

from src.ingest.rawlog import Turn
from src.labeling.course import CourseProfile
from src.labeling.draft import (COVERAGE_PROMPT, FORM_TAXONOMY,
                                MOVE_TAXONOMY, SINGLE_LABEL_PROMPT,
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
    # Golden literal pins BOTH templates, the profile rendering, the window
    # rendering, and the coverage-call labels-block rendering (the
    # "- {name}: {description}" line format). Any intentional change to
    # those must update this literal — that update, and only that update,
    # is the point of the test.
    # 840c1db2c5ad: context-timing vintage (2026-08-07) — latency line in
    # _SHARED_CONTEXT + move instruction/taxonomy + bucket thresholds.
    # re-vintaged 2026-08-09 (2nd): sequence rendering + qref patterns
    # folded into hash (rule 2)
    h = classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE)
    assert h == "fc36005bb9ed"


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


def test_on_result_exception_propagates_and_keeps_finished_messages():
    def gen(prompt, response_model):
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        return CoverageVerdict(no_label_fits=False)

    def on_result(m, r):
        if m.message_index == 1:
            raise ValueError("callback boom")
        delivered.append(m.message_index)

    msgs = [_msg_i(i) for i in range(3)]
    delivered = []
    try:
        draft_labels(msgs, SCHEMA, PROFILE, gen, workers=1,
                     on_result=on_result)
        raise AssertionError("should have raised")
    except ValueError as e:
        assert str(e) == "callback boom"
    # workers=1 is sequential: message 0 completed and was delivered before
    # message 1's on_result raised; message 2 never ran.
    assert delivered == [0]


def test_forms_land_filtered_and_ordered():
    def gen(prompt, response_model):
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=False, rationale="r")
        return CoverageVerdict(forms=["pasted-assignment", "invented-form",
                                      "authored-question"],
                               no_label_fits=False)

    out = draft_labels([_msg()], SCHEMA, PROFILE, gen)
    # unknown form names dropped, taxonomy order NOT imposed (model order kept)
    assert out[0].forms == ["pasted-assignment", "authored-question"]


def test_forms_default_parses_old_snapshots():
    r = MessageLabels(chatlog_id=1, message_index=0, labels={}, rationales={})
    assert r.forms == []


def test_coverage_prompt_carries_form_taxonomy():
    gen = make_fake()
    draft_labels([_msg()], SCHEMA, PROFILE, gen)
    cov = [p for k, p in gen.calls if k == "CoverageVerdict"]
    assert len(cov) == 1
    for form in FORM_TAXONOMY:
        assert form in cov[0]
    # declared before the coverage question so the model commits to the
    # surface reading first
    assert cov[0].index("pasted-assignment") < cov[0].index("no_label_fits")


def _v2_profile():
    from src.labeling.profile2 import ConceptDef, CourseProfileV2
    return CourseProfileV2(
        base=PROFILE,
        concepts=[
            ConceptDef(name="loops", description="iteration"),
            ConceptDef(name="tables", description="tabular data"),
            ConceptDef(name="promoted-one", description="p", promoted=True,
                       positive_criteria="p", negative_criteria="n")],
        affect_labels=[], intent_labels=[], explored_on="2026-08-07",
        corpus_sample={"conversations": 1, "seed": 0},
        materials_provided=False, repo_sha="x", accepted=True)


def test_concepts_land_filtered_and_default():
    def gen(prompt, response_model):
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=False, rationale="r")
        return CoverageVerdict(concepts=["loops", "hallucinated"],
                               no_label_fits=False)

    out = draft_labels([_msg()], SCHEMA, PROFILE, gen,
                       profile2=_v2_profile())
    assert out[0].concepts == ["loops"]
    # without a v2 profile the field defaults empty and old snapshots parse
    r = MessageLabels(chatlog_id=1, message_index=0, labels={},
                      rationales={})
    assert r.concepts == []


def test_coverage_prompt_lists_nonpromoted_concepts_only():
    gen = make_fake()
    draft_labels([_msg()], SCHEMA, PROFILE, gen, profile2=_v2_profile())
    cov = [p for k, p in gen.calls if k == "CoverageVerdict"][0]
    assert "loops" in cov and "tables" in cov
    assert "promoted-one" not in cov
    # single-label prompts unaffected by the concept block
    single = [p for k, p in gen.calls if k == "SingleLabelVerdict"][0]
    assert "loops" not in single


def test_latency_line_in_both_prompts():
    gen = make_fake()
    draft_labels([_msg(latency_seconds=250.0, latency_bucket="working")],
                 SCHEMA, PROFILE, gen)
    for _, p in gen.calls:
        assert "Time since the tutor's last message: 4 minutes (working)" in p


def test_latency_line_opening_and_unknown():
    gen = make_fake()
    draft_labels([_msg(latency_bucket="conversation-opening"),
                  _msg(message_index=4)], SCHEMA, PROFILE, gen)
    prompts = [p for _, p in gen.calls]
    assert any("message: (conversation opening)" in p for p in prompts)
    assert any("message: (unknown)" in p for p in prompts)


def test_move_lands_filtered_and_defaults():
    def gen(prompt, response_model):
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=False, rationale="r")
        return CoverageVerdict(move="responds-to-tutor", no_label_fits=False)

    out = draft_labels([_msg(latency_seconds=10.0, latency_bucket="rapid")],
                       SCHEMA, PROFILE, gen)
    assert out[0].move == "responds-to-tutor"
    assert out[0].latency_seconds == 10.0
    assert out[0].latency_bucket == "rapid"

    def gen_bad(prompt, response_model):
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=False, rationale="r")
        return CoverageVerdict(move="hallucinated-move", no_label_fits=False)

    out = draft_labels([_msg()], SCHEMA, PROFILE, gen_bad)
    assert out[0].move == ""
    r = MessageLabels(chatlog_id=1, message_index=0, labels={},
                      rationales={})
    assert r.move == "" and r.latency_seconds is None
    assert r.latency_bucket == ""


def test_coverage_prompt_carries_move_taxonomy():
    gen = make_fake()
    draft_labels([_msg()], SCHEMA, PROFILE, gen)
    cov = [p for k, p in gen.calls if k == "CoverageVerdict"][0]
    for mv in MOVE_TAXONOMY:
        assert mv in cov


def test_v1_golden_hash_unchanged_and_v2_hash_moves():
    # re-vintaged 2026-08-09 (2nd): sequence rendering + qref patterns
    # folded into hash (rule 2)
    h1 = classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE)
    assert h1 == "fc36005bb9ed"          # v1 path: sequence-context vintage
    v2 = _v2_profile()
    h2 = classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE, profile2=v2)
    assert h2 != h1
    edited = v2.model_copy(update={"concepts": v2.concepts[:1]})
    assert classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE,
                           profile2=edited) != h2


def test_sequence_render_lines():
    from src.labeling.draft import _render_mode, _render_sequence
    m = _msg(pre_pattern="fail-then-ask", last_run_minutes=4.2,
             last_run_grader="q3_2", last_run_success=False,
             snapshot_traceback=True, seq_granularity="question",
             mode="chatgpt")
    s = _render_sequence(m)
    assert "4m" in s and "FAILED" in s and "q3_2" in s
    # traceback is a conversation-start snapshot flag, not live state
    assert "notebook snapshot at conversation start showed a traceback" in s
    assert "question-level" in s
    empty = _render_sequence(_msg())
    assert "No autograder data" in empty
    ask_first = _render_sequence(_msg(pre_pattern="ask-first",
                                      seq_granularity="notebook"))
    # honest windowed claim (finding 1): 45 comes from BEFORE_MIN, not
    # hardcoded, and this line is distinct from the no-data line above
    from src.ingest.sequences import BEFORE_MIN
    assert BEFORE_MIN == 45
    assert ("No autograder activity in the 45 min before this message"
            in ask_first)
    assert ask_first != empty
    assert "plain-ChatGPT mode" in _render_mode(m)
    assert "tutor" in _render_mode(_msg(mode="tutor")).lower()
    assert "unknown" in _render_mode(_msg()).lower()


def test_mechanical_facets_copied_not_judged():
    # fake generate returns applies=True for everything; facets must come
    # from the SampledMessage, untouched by the model
    gen = make_fake()
    msgs = [_msg(pre_pattern="ask-first", mode="chatgpt",
                 snapshot_traceback=False)]
    out = draft_labels(msgs, SCHEMA, PROFILE, gen)
    r = out[0]
    assert r.mode == "chatgpt" and r.attempted is False
    assert r.error_verified is False and r.pre_pattern == "ask-first"
    legacy = draft_labels([_msg()], SCHEMA, PROFILE, gen)[0]
    assert legacy.attempted is None and legacy.error_verified is None


def test_hash_covers_sequence_rendering():
    HASH_BEFORE_SEQUENCE = "840c1db2c5ad"
    h1 = classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE)
    assert h1 != HASH_BEFORE_SEQUENCE   # vintage moved, deliberately
