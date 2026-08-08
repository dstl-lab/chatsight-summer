"""Blind-audit web tool (Phase 0). Serves a stratified audit sample from a
snapshot WITHOUT model labels anywhere in the payload (invariant 8 —
anchoring shifts human labels toward the model, ACL Findings 2025). Sample
composition comes from eval.audit_sample: abstained stratum first, then
high-entropy when available, then seeded random. Answers land in
data/audit/<snapshot_id>/human-labels-<annotator>.json. 127.0.0.1 only
(rule 4)."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from src.eval.audit_sample import build_audit_sample
from src.ingest.rawlog import Conversation
from src.labeling.draft import MessageLabels
from src.labeling.sampler import stratified_sample
from src.labeling.schema import LabelSchema

PAGE = """<!doctype html><meta charset="utf-8">
<title>blind audit</title>
<style>
body{font:15px -apple-system,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem}
.ctx{color:#666;font-size:13px;white-space:pre-wrap;border-left:3px solid #ddd;padding-left:8px;margin:4px 0;max-height:150px;overflow-y:auto}
.msg{background:#f5f2ea;padding:10px;border-radius:6px;white-space:pre-wrap;margin:10px 0;font-weight:600}
.lbl{display:block;margin:6px 0;padding:8px;border:1px solid #ddd;border-radius:6px;cursor:pointer;border-left-width:5px}
.lbl small{color:#666;display:block}
.lbl input{margin-right:8px}
.cat-instructor{border-left-color:#b8860b;background:#fdf9ee}
.cat-intent{border-left-color:#2b6cb0;background:#f2f7fc}
.cat-affect{border-left-color:#c53060;background:#fdf2f6}
.cat-concept{border-left-color:#2f855a;background:#f2faf5}
.legend{font-size:12px;color:#555;margin:8px 0}
.legend span{display:inline-block;padding:2px 8px;border-radius:4px;margin-right:6px;border-left:5px solid}

.sect{font-size:11px;letter-spacing:.08em;color:#999;margin:14px 0 4px;font-weight:700}
.nav{margin:16px 0;display:flex;gap:8px;align-items:center}
button{padding:8px 14px}
#done{display:none;font-weight:600}
.warn{background:#fff6e0;padding:8px;border-radius:6px;font-size:13px}
</style>
<h2>Blind audit — <span id="pos"></span> of <span id="total"></span></h2>
<p class="warn">Model labels are hidden by design. Judge the student's act in
THIS message using the context. Check every label that applies; check
"no label fits" if the message shows an act none of the labels capture.</p>
<div class="sect" id="ctx-head">CONVERSATION BEFORE — context only</div>
<div id="ctx"></div>
<div class="sect">▼ THE STUDENT MESSAGE YOU ARE LABELING</div>
<div class="msg" id="msg"></div>
<div class="sect" id="after-head">TUTOR REPLY AFTER — context only</div>
<div class="ctx" id="after"></div>
<div class="legend">
<span class="cat-instructor">instructor</span>
<span class="cat-intent">intent</span>
<span class="cat-affect">affect</span>
<span class="cat-concept">concept</span>
</div>
<div id="labels"></div>
<label class="lbl"><input type="checkbox" id="nofit"><b>no label fits</b>
<small>a student act none of the labels capture</small></label>
<div class="nav">
<button id="prev">← Prev</button><button id="next">Next →</button>
<button id="save" style="display:none">Submit all</button>
<span id="done">Saved. Thanks — you can close this tab.</span>
</div>
<script>
const D = __PAYLOAD__;
let i = 0;
const ans = D.messages.map(() => ({labels:{}, no_label_fits:false}));
document.getElementById("total").textContent = D.messages.length;
function render(){
  const m = D.messages[i];
  document.getElementById("pos").textContent = i+1;
  const ctx = document.getElementById("ctx"); ctx.replaceChildren();
  for (const t of m.context){
    const d = document.createElement("div"); d.className = "ctx";
    d.textContent = t.role + ": " + t.text; ctx.append(d);
  }
  document.getElementById("ctx-head").style.display = m.context.length ? "block" : "none";
  document.getElementById("msg").textContent = m.text;
  document.getElementById("after").textContent = m.after;
  document.getElementById("after-head").style.display = m.after ? "block" : "none";
  const box = document.getElementById("labels"); box.replaceChildren();
  for (const l of D.labels){
    const lab = document.createElement("label");
    lab.className = "lbl cat-" + l.category;
    const cb = document.createElement("input"); cb.type = "checkbox";
    cb.checked = !!ans[i].labels[l.name];
    cb.onchange = () => ans[i].labels[l.name] = cb.checked;
    const b = document.createElement("b"); b.textContent = l.name;
    const s = document.createElement("small");
    s.textContent = l.description + " — applies: " + l.positive + " | not: " + l.negative;
    lab.append(cb, b, s); box.append(lab);
  }
  const nf = document.getElementById("nofit");
  nf.checked = ans[i].no_label_fits;
  nf.onchange = () => ans[i].no_label_fits = nf.checked;
  document.getElementById("save").style.display =
    (i === D.messages.length-1) ? "inline-block" : "none";
}
document.getElementById("prev").onclick = () => { if (i>0){i--; render();} };
document.getElementById("next").onclick = () => { if (i<D.messages.length-1){i++; render();} };
document.getElementById("save").onclick = async () => {
  const body = D.messages.map((m, k) => ({key: m.key, ...ans[k]}));
  const r = await fetch("/save", {method:"POST",
    headers:{"content-type":"application/json"}, body: JSON.stringify(body)});
  if (r.ok) document.getElementById("done").style.display = "inline";
};
render();
</script>"""


def _categories(schema: LabelSchema, profile_path: Path | None
                ) -> dict[str, str]:
    """instructor | intent | affect | concept per label name. Layer
    membership comes from the profile artifact; labels absent from it are
    the instructor's (fallback: promoted-concept kinds map to concept)."""
    cats = {l.name: ("concept" if l.kind == "conceptual" else "instructor")
            for l in schema.labels}
    if profile_path is not None:
        from src.labeling.profile2 import load_profile
        v2 = load_profile(profile_path)
        for l in v2.affect_labels:
            if l.name in cats:
                cats[l.name] = "affect"
        for l in v2.intent_labels:
            if l.name in cats:
                cats[l.name] = "intent"
        for c in v2.concepts:
            if c.promoted and c.name in cats:
                cats[c.name] = "concept"
    return cats


def build_payload(snapshot_dir: Path, n: int, seed: int,
                  exclude_review_sample_size: int | None = None,
                  profile_path: Path | None = None) -> dict:
    conversations = [Conversation.model_validate_json(l)
                     for l in (snapshot_dir / "conversations.jsonl").open()]
    schema = LabelSchema.model_validate_json(
        (snapshot_dir / "schema.json").read_text())
    rows = [MessageLabels.model_validate_json(l)
            for l in (snapshot_dir / "labels.jsonl").open()]
    exclude = set()
    if exclude_review_sample_size:
        exclude = {(m.chatlog_id, m.message_index) for m in stratified_sample(
            conversations, n=exclude_review_sample_size, seed=seed)}
    sample = build_audit_sample(rows, n=n, seed=seed, exclude=exclude)
    by_key = {}
    for m in stratified_sample(conversations, n=10**9, seed=seed):
        by_key[(m.chatlog_id, m.message_index)] = m
    picked = [by_key[k] for k in sample["keys"]]
    cats = _categories(schema, profile_path)
    return {
        "labels": [{"name": l.name, "description": l.description,
                    "positive": l.positive_criteria,
                    "negative": l.negative_criteria,
                    "category": cats[l.name]}
                   for l in schema.labels],
        "messages": [{
            "key": [m.chatlog_id, m.message_index],
            "context": [{"role": t.role, "text": t.text} for t in m.context],
            "text": m.text, "after": m.context_after or "",
        } for m in picked],
        "strata": {f"{k[0]}:{k[1]}": v for k, v in sample["strata"].items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Blind-audit server")
    parser.add_argument("snapshot_dir")
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--annotator", default="minchan")
    parser.add_argument("--exclude-review-sample", type=int, default=None,
                        help="review sample_size of the original run — "
                             "those messages are anchored (invariant 8)")
    parser.add_argument("--port", type=int, default=8399)
    parser.add_argument("--profile", default=None,
                        help="profile artifact for layer color-coding")
    args = parser.parse_args()

    snap = Path(args.snapshot_dir)
    payload = build_payload(snap, args.n, args.seed,
                            args.exclude_review_sample,
                            Path(args.profile) if args.profile else None)
    out = (snap.parent.parent / "audit" / snap.name /
           f"human-labels-{args.annotator}.json")

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            html = PAGE.replace("__PAYLOAD__", json.dumps(payload))
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())

        def do_POST(self):
            n_ = int(self.headers["content-length"])
            data = json.loads(self.rfile.read(n_))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(data, indent=2))
            self.send_response(200)
            self.end_headers()
            print("saved", out, flush=True)

        def log_message(self, *a):
            pass

    strata = payload["strata"].values()
    print(f"blind audit on http://127.0.0.1:{args.port} — "
          f"{len(payload['messages'])} messages "
          f"({sum(1 for s in strata if s == 'abstained')} abstained, "
          f"{sum(1 for s in strata if s == 'random')} random)", flush=True)
    HTTPServer(("127.0.0.1", args.port), H).serve_forever()


if __name__ == "__main__":
    main()
