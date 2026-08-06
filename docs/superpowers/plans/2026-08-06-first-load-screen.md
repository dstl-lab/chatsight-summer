# First-Load Screen Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the idle screen of the labeling web UI into an instructor-facing surface: bookend plate header, large writing surface, a side rail of real stratified messages (data peek), and collapsed run settings.

**Architecture:** One new read-only `LoopSession.peek()` method exposed as `GET /api/peek` in the existing FastAPI app (`src/labeling/webapp.py`); frontend changes are confined to the `screen-idle` section, CSS, and idle-screen JS in the single-file UI (`src/labeling/static/index.html`). Spec: `docs/superpowers/specs/2026-08-06-first-load-screen-design.md`.

**Tech Stack:** Python 3 / FastAPI / pydantic backend, vanilla-JS single-file frontend, pytest with the existing hermetic fakes in `tests/test_webapp.py` (no DB, no Gemini, no network).

## Global Constraints

- Student text in the DOM is set with `textContent` only, never `innerHTML` (standing rule in `index.html`).
- Peek data is display-only: never persisted, never part of a snapshot, no mutation of session state.
- `/api/peek` is valid only in the `idle` phase; peek's conversation fetch cap is exactly 40.
- Run-knob defaults unchanged: max conversations 200, sample size 25, seed 0.
- `ELICIT_PROMPT` and everything in `src/labeling/elicit.py` are untouched.
- Working/review/done/error screens and all existing endpoints keep their current behavior.
- Copy (verbatim): plate stamp `label-loop · new run`; headline `What do you want to see in your course's tutor chats?`; button `Draft labels from this →`; peek loading `reading your course's chats…`; peek failure `Couldn't reach the chat logs — is bin/tunnel running?` (with `bin/tunnel` in a `<code>` element).

---

### Task 1: `/api/peek` backend

**Files:**
- Modify: `src/labeling/webapp.py` (LoopSession + FastAPI layer)
- Test: `tests/test_webapp.py`

**Interfaces:**
- Consumes: `stratified_sample(conversations, n, seed)` and `SampledMessage` from `src/labeling/sampler.py` (already imported in webapp.py); `self.fetch(ext_db_url, limit)` (same callable `start()` uses; the test fake has signature `fake_fetch(url, limit, on_progress=None)`); `Conversation.student_turns` from `src/ingest/rawlog.py`.
- Produces: `LoopSession.peek(n: int = 6, seed: int = 0) -> dict` returning `{"messages": [{"text": str, "stratum": str}], "total_messages": int}` where `stratum` is plain words (e.g. `"short conversation · early turn"`, never raw `"short/early"`); `GET /api/peek?n=&seed=` returning that dict (409 via the existing `PhaseError` handler when not idle). Task 3's frontend relies on exactly these field names.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webapp.py` (it already imports `pytest`, `PhaseError`, `make_session`, `CONVS`, and — in the FastAPI section — `TestClient` and `create_app`):

```python
# --- /api/peek (first-load data peek) --------------------------------------

def test_peek_returns_plain_word_stratified_messages(tmp_path):
    session = make_session(tmp_path)
    out = session.peek(n=3, seed=0)
    assert len(out["messages"]) == 3
    for m in out["messages"]:
        assert m["text"]
        assert " · " in m["stratum"]      # plain words with a separator...
        assert "/" not in m["stratum"]    # ...never the raw "short/early" key
    assert out["total_messages"] == sum(len(c.student_turns) for c in CONVS)


def test_peek_rejected_outside_idle(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    with pytest.raises(PhaseError):
        session.peek()


def test_peek_does_not_mutate_session_state(tmp_path):
    session = make_session(tmp_path)
    session.peek()
    assert session.state()["phase"] == "idle"
    assert session.conversations == []    # display-only: nothing retained


def test_peek_fetch_is_capped_at_40(tmp_path):
    session = make_session(tmp_path)
    seen = {}
    orig = session.fetch

    def spy(url, limit, on_progress=None):
        seen["limit"] = limit
        return orig(url, limit, on_progress)

    session.fetch = spy
    session.peek()
    assert seen["limit"] == 40


def test_peek_endpoint_shape_and_phase_guard(tmp_path):
    session = make_session(tmp_path)
    client = TestClient(create_app(session))
    r = client.get("/api/peek?n=2&seed=1")
    assert r.status_code == 200
    assert len(r.json()["messages"]) == 2
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    assert client.get("/api/peek").status_code == 409
```

Note: if `TestClient` / `create_app` are imported mid-file in the FastAPI test
section rather than at the top, place the endpoint test after those imports.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_webapp.py -k peek -v`
Expected: FAIL — `AttributeError: 'LoopSession' object has no attribute 'peek'` (and 404 for the endpoint test).

- [ ] **Step 3: Implement `peek()` and the endpoint**

In `src/labeling/webapp.py`, below `WORKING_PHASES`, add the cap and the stratum wording helper:

```python
PEEK_FETCH_CAP = 40   # conversations; spec: docs/superpowers/specs/2026-08-06

_TERCILE_WORDS = {"short": "short conversation", "mid": "medium conversation",
                  "long": "long conversation"}
_POSITION_WORDS = {"early": "early turn", "late": "late turn"}


def _plain_stratum(stratum: str) -> str:
    tercile, _, position = stratum.partition("/")
    return (f"{_TERCILE_WORDS.get(tercile, tercile)} · "
            f"{_POSITION_WORDS.get(position, position)}")
```

Add the method to `LoopSession` (e.g. right before `state()`):

```python
    def peek(self, n: int = 6, seed: int = 0) -> dict:
        """Display-only sample for the idle screen. Reads through the tunnel
        but retains nothing: no session state, no snapshot contact."""
        with self._lock:
            self._require("idle")
        n = max(1, min(12, n))
        convs = self.fetch(self.ext_db_url, PEEK_FETCH_CAP)
        picks = stratified_sample(convs, n=n, seed=seed)
        return {
            "messages": [{"text": m.text,
                          "stratum": _plain_stratum(m.stratum)}
                         for m in picks],
            "total_messages": sum(len(c.student_turns) for c in convs),
        }
```

Add the route in `create_app` (next to `/api/examples`):

```python
    @app.get("/api/peek")
    def peek(n: int = 6, seed: int = 0) -> dict:
        return session.peek(n=n, seed=seed)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_webapp.py -v`
Expected: all PASS (new peek tests and every pre-existing test).

- [ ] **Step 5: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py
git commit -m "feat: idle-only /api/peek endpoint for the first-load data peek"
```

---

### Task 2: idle screen structure — plate, two columns, collapsed run settings

**Files:**
- Modify: `src/labeling/static/index.html` (the `#screen-idle` section, the `<style>` block, and one line of `render()`)

**Interfaces:**
- Consumes: existing CSS components `.plate`, `.plate-stamp`, `.plate-intent`, `.plate-lede`, `.layout`, `.stratum`; existing element ids `intent`, `max-conversations`, `sample-size`, `seed`, `btn-start` (their JS wiring at the bottom of the file must keep working unchanged).
- Produces: new element ids `peek-head` and `peek-body` (Task 3 renders into these); CSS classes `.idle-layout`, `.peek-rail`, `.run-settings`.

- [ ] **Step 1: Replace the `#screen-idle` markup**

Replace the current section (`index.html:135-143`) with:

```html
<section id="screen-idle" class="hidden">
  <div class="plate">
    <div class="plate-stamp">label-loop · new run</div>
    <div class="plate-intent">What do you want to see in your course's tutor chats?</div>
    <div class="plate-lede">Describe the trends you care about — topics students
      struggle with, help-seeking behavior, affect. Your words become the label
      schema; you'll review a labeled sample before anything is final.</div>
  </div>
  <div class="layout idle-layout">
    <div class="action">
      <textarea id="intent" rows="6"
        placeholder="Brief the labeler like you'd brief a TA — the more specific about what matters to you, the sharper the labels."></textarea>
      <button id="btn-start">Draft labels from this →</button>
      <details class="run-settings">
        <summary>run settings</summary>
        <label>Max conversations <input id="max-conversations" type="number" value="200"></label>
        <label>Sample size <input id="sample-size" type="number" value="25"></label>
        <label>Seed <input id="seed" type="number" value="0"></label>
      </details>
    </div>
    <div class="peek-rail">
      <div class="stratum" id="peek-head">What students sounded like</div>
      <div id="peek-body"></div>
    </div>
  </div>
</section>
```

This removes the old static footnote line (`Reads the raw-log DB through the tunnel — is <code>bin/tunnel</code> running?`) — Task 3's peek failure state replaces it. The three number inputs keep their ids and defaults, so the existing `btn-start` click handler needs no change.

Leave the page-level `<h1>label-loop</h1>` exactly where it is: the other four screens rely on it, and the plate stamp naming the product twice on the idle screen is acceptable. Do not restructure the h1 in this task.

- [ ] **Step 2: Add idle-screen CSS**

In the `<style>` block, after the `/* done screen */` rules, add:

```css
  /* idle screen */
  .idle-layout .action { flex: 1.6; }
  .peek-rail { flex: 1; min-width: 0; }
  .peek-msg { font-size: .84rem; font-style: italic; opacity: .85;
    border-left: 2px solid rgba(128,128,128,.35); padding-left: .6rem;
    margin: .55rem 0; }
  .peek-msg .meta { display: block; font-style: normal; font-size: .72rem;
    opacity: .6; }
  .run-settings { margin-top: 1rem; font-size: .85rem; }
  .run-settings summary { cursor: pointer; opacity: .7; }
  .run-settings label { display: block; margin-top: .5rem; }
```

And in `render()` (bottom of the file), widen the page on idle as well as during work, so the two-column idle layout has room:

```js
  document.body.classList.toggle("wide", working || phase === "idle");
```

(currently `document.body.classList.toggle("wide", working);`)

- [ ] **Step 3: Verify by loading the app**

Run: `python -m src.labeling.webapp` (needs `GEMINI_API_KEY` in `.env`; the tunnel is NOT needed for this step) and open `http://127.0.0.1:8321`.
Expected: plate header with stamp/headline/lede; textarea (6 rows, placeholder) and `Draft labels from this →` on the left; empty peek rail headed "What students sounded like" on the right; "run settings" collapsed, expanding to the three inputs with defaults 200 / 25 / 0; columns stack on a narrow window.

- [ ] **Step 4: Commit**

```bash
git add src/labeling/static/index.html
git commit -m "feat: bookend idle screen — plate header, writing surface, collapsed run settings"
```

---

### Task 3: data peek rail behavior

**Files:**
- Modify: `src/labeling/static/index.html` (script section only)

**Interfaces:**
- Consumes: `GET /api/peek?n=6&seed=<int>` → `{"messages": [{"text", "stratum"}], "total_messages"}` (Task 1); elements `#peek-head` / `#peek-body` and class `.peek-msg` (Task 2); existing helpers `$()` and `linkButton(text, onActivate)`.
- Produces: `loadPeek()`; a `peekLoaded` guard flag consulted in `render()`.

- [ ] **Step 1: Add peek loading/rendering JS**

In the script, after the `linkButton` helper, add:

```js
// --- idle-screen data peek -------------------------------------------------
// Loads once per visit to the idle screen; doubles as a live tunnel check
// (if the sample renders, bin/tunnel is provably up before Start).
let peekLoaded = false;

function peekStatus(text) {
  const p = document.createElement("p");
  p.className = "provenance";
  p.textContent = text;
  return p;
}

async function loadPeek() {
  const head = $("peek-head"), body = $("peek-body");
  head.replaceChildren();
  head.append("What students sounded like");
  body.replaceChildren(peekStatus("reading your course's chats…"));
  try {
    const seed = Math.floor(Math.random() * 1e6);
    const r = await fetch(`/api/peek?n=6&seed=${seed}`);
    if (!r.ok) throw new Error("peek failed: " + r.status);
    const data = await r.json();
    head.replaceChildren();
    head.append(`What students sounded like — ${data.messages.length} of ` +
                `${data.total_messages.toLocaleString()} messages · `);
    head.append(linkButton("resample", loadPeek));
    body.replaceChildren();
    // student text: always textContent, never innerHTML
    for (const m of data.messages) {
      const div = document.createElement("div");
      div.className = "peek-msg";
      div.textContent = `“${m.text}”`;
      const meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = m.stratum;
      div.append(meta);
      body.append(div);
    }
  } catch (e) {
    body.replaceChildren();
    const fail = peekStatus("Couldn't reach the chat logs — is ");
    const code = document.createElement("code");
    code.textContent = "bin/tunnel";
    fail.append(code, " running? ");
    fail.append(linkButton("retry", loadPeek));
    body.append(fail);
  }
}
```

- [ ] **Step 2: Trigger it from `render()`**

In `render()`, extend the idle branch (currently `if (phase === "idle") { doneRendered = null; show("idle"); }`):

```js
  if (phase === "idle") {
    doneRendered = null;
    if (!peekLoaded) { peekLoaded = true; loadPeek(); }
    show("idle");
  }
```

and reset the guard when leaving idle — add to the final `else`-reachable common path by placing this line just before the `if (phase === "idle")` chain:

```js
  if (phase !== "idle") peekLoaded = false;
```

(The 1.5 s `refresh()` poll re-runs `render()` constantly; the guard makes the peek load once per arrival at the idle screen, and again after a run completes and the user starts a new one.)

- [ ] **Step 3: Verify the failure state (no tunnel)**

With the tunnel down, reload `http://127.0.0.1:8321`.
Expected: rail shows "reading your course's chats…" briefly, then "Couldn't reach the chat logs — is `bin/tunnel` running? retry"; clicking retry repeats the cycle; Start remains enabled.

- [ ] **Step 4: Verify the success state (tunnel up)**

Start `bin/tunnel`, click retry (or reload).
Expected: header becomes "What students sounded like — 6 of N messages · resample"; six italic student quotes each with a plain-word meta line ("short conversation · early turn" style); resample swaps in different messages; starting a run leaves peek behavior untouched, and quitting back to idle reloads the peek.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/static/index.html
git commit -m "feat: live data peek rail on the idle screen with resample and tunnel check"
```
