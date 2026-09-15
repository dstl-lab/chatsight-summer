"""Snapshot-only episode review, served on localhost; human answers stay separate."""
import argparse
import fcntl
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.labeling.episodes import load_bundle

DIMENSIONS = {"request": ("request", "student"),
              "tutor_response": ("response", "tutor"),
              "followup": ("followup", "student")}
UNKNOWN = {"unclear", "insufficient-evidence", "no-followup-observed"}
CONDITIONS = ("baseline", "timeline", "annotated")


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    turn_id: str
    quote: str = Field(min_length=1)


class Judgment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    value: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    rationale: str = ""
    assessment: Literal["accepted", "changed", "cannot-assess"] | None = None


class InstructorAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = ""
    evidence: list[Evidence] = Field(default_factory=list)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    episode_id: str
    revision: int = Field(default=0, ge=0)
    judgments: dict[str, Judgment] = Field(default_factory=dict)
    instructor_action: InstructorAction = Field(default_factory=InstructorAction)
    elapsed_ms: int = Field(default=0, ge=0)
    complete: bool = False
    workflow: Literal["manual", "draft-review"] = "manual"


def _validate_review(review: Review, episode: dict, rubric: dict, task: str) -> None:
    def evidence_valid(evidence, turns):
        by_id = {turn["id"]: turn for turn in turns}
        for span in evidence:
            if (span.turn_id not in by_id or not span.quote.strip()
                    or span.quote not in by_id[span.turn_id]["text"]):
                raise ValueError("Evidence must quote an exact nonempty span from an eligible turn.")

    if set(review.judgments) - DIMENSIONS.keys():
        raise ValueError("Unknown judgment dimension.")
    if task != "development" and (review.workflow == "draft-review" or any(
            judgment.assessment is not None for judgment in review.judgments.values())):
        raise ValueError("Draft review decisions are only available in development.")
    for dimension, (phase, role) in DIMENSIONS.items():
        judgment = review.judgments.get(dimension)
        if judgment is None:
            if review.complete:
                raise ValueError("Complete reviews need all three judgments.")
            continue
        if review.complete and review.workflow == "draft-review" and judgment.assessment is None:
            raise ValueError(f"Choose accept, change, or cannot assess for {dimension}.")
        if judgment.assessment == "cannot-assess":
            if judgment.value is not None or judgment.evidence:
                raise ValueError("Cannot assess is a reviewer decision, with no category or evidence.")
            continue
        if judgment.assessment == "accepted":
            draft = (episode.get("annotation") or {}).get(dimension)
            if (not draft or judgment.value != draft["value"]
                    or [span.model_dump() for span in judgment.evidence] != draft["evidence"]):
                raise ValueError("Accepted judgments must match the draft category and evidence.")
        turns = [turn for turn in episode["turns"]
                 if turn["phase"] == phase and turn["role"] == role]
        value = judgment.value
        if value and value not in rubric[dimension]["options"]:
            raise ValueError(f"Unknown value for {dimension}.")
        if dimension == "followup" and value:
            if (value == "no-followup-observed") != (not turns):
                raise ValueError("Use no-followup-observed only when there are no follow-up turns.")
        evidence_valid(judgment.evidence, turns)
        if review.complete and (not value or (value not in UNKNOWN and not judgment.evidence)):
            raise ValueError(f"A complete {dimension} judgment needs a value and supporting evidence.")
    evidence_valid(review.instructor_action.evidence, episode["context"] + episode["turns"])


def create_app(bundle_path: Path, reviewer: str, task: str = "development",
               cohort: int = 0, split: str | None = None) -> FastAPI:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", reviewer):
        raise ValueError("reviewer must use 1–64 letters, digits, underscores, or hyphens.")
    if task not in {"development", "coding", "comparison"}:
        raise ValueError("Unknown review task.")
    if type(cohort) is not int or cohort not in (0, 1, 2):
        raise ValueError("cohort must be 0, 1, or 2.")
    split = split or ("development" if task == "development" else "holdout")
    if split not in {"development", "holdout"}:
        raise ValueError("Unknown split.")
    if task == "development" and split != "development":
        raise ValueError("The development task cannot expose the holdout split.")

    bundle_path = Path(bundle_path)
    bundle = load_bundle(bundle_path)
    rubric = bundle["rubric"]
    if set(rubric) != DIMENSIONS.keys() or any(
        not isinstance(rubric[d].get("options"), dict) or not rubric[d]["options"]
        for d in DIMENSIONS
    ):
        raise ValueError("Bundle needs three rubric dimensions with named options.")
    episodes = [ep for ep in bundle["episodes"] if ep["split"] == split]
    by_id = {ep["id"]: ep for ep in episodes}
    if len(by_id) != len(episodes):
        raise ValueError("Duplicate episode IDs.")
    for ep in episodes:
        turns = ep["context"] + ep["turns"]
        if len({turn["id"] for turn in turns}) != len(turns):
            raise ValueError("Duplicate turn IDs in an episode.")
        if any(turn["role"] not in {"student", "tutor"}
               or not isinstance(turn["text"], str) for turn in turns):
            raise ValueError("Every turn needs a valid role and text.")

    conditions = {ep["id"]: (CONDITIONS[(i + cohort) % 3] if task == "comparison"
                             else "annotated" if task == "development" else "timeline")
                  for i, ep in enumerate(episodes)}
    if task == "comparison" and any(
        conditions[ep["id"]] == "annotated" and not ep.get("annotation") for ep in episodes
    ):
        raise ValueError("Comparison needs draft annotations for every assigned annotated episode; annotate this split first.")

    # Explicit allowlist: model output and preparation diagnostics never enter blind payloads.
    visible = []
    for ep in episodes:
        item = {key: ep[key] for key in ("id", "split", "conversation_key", "notebook",
                                        "question_ref", "question_link", "context", "turns", "limitations")}
        item["condition"] = conditions[ep["id"]]
        if item["condition"] == "annotated":
            item["annotation"] = ep.get("annotation")
        if item["condition"] == "baseline":
            item["legacy_labels"] = ep.get("legacy_labels", [])
        visible.append(item)

    out = bundle_path.parent / "reviews" / f"{task}-{split}-{reviewer}.json"
    identity = {"manifest": bundle["manifest"], "rubric": rubric, "reviewer": reviewer,
                "task": task, "split": split, "cohort": cohort}

    def read_saved():
        if not out.exists():
            return {**identity, "reviews": {}}
        saved = json.loads(out.read_text())
        if any(saved.get(key) != value for key, value in identity.items()):
            raise ValueError("Existing review file conflicts with this manifest, rubric, reviewer, task, split, or cohort.")
        if not isinstance(saved.get("reviews"), dict) or set(saved["reviews"]) - by_id.keys():
            raise ValueError("Existing reviews contain invalid episode references; the file was preserved.")
        for episode_id, answer in saved["reviews"].items():
            if answer.get("episode_id") != episode_id or answer.get("condition") != conditions[episode_id]:
                raise ValueError("Existing review condition or episode conflicts with this session.")
            _validate_review(Review.model_validate({k: v for k, v in answer.items()
                                                   if k in Review.model_fields}), by_id[episode_id], rubric, task)
        return saved

    read_saved()  # Fail before serving if a previous session cannot safely resume.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        if request.method == "POST":
            origin = request.headers.get("origin")
            expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
            if (origin is not None and origin != expected
                    or request.headers.get("sec-fetch-site") == "cross-site"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Review writes must come from this local page."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; img-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        return response

    @app.get("/", response_class=HTMLResponse)
    def page():
        return Path(__file__).with_suffix(".html").read_text()

    @app.get("/api/session")
    def session():
        try:
            saved = read_saved()
        except (OSError, ValueError, TypeError) as error:
            raise HTTPException(409, f"Cannot resume saved progress: {error}") from error
        return {"manifest": {k: bundle["manifest"].get(k) for k in
                             ("bundle_id", "snapshot_id", "seed", "rubric_hash")},
                "question": bundle["question"], "rubric": rubric, "reviewer": reviewer,
                "task": task, "split": split, "cohort": cohort, "episodes": visible,
                "reviews": saved["reviews"]}

    @app.post("/api/review")
    def save_review(review: Review):
        if review.episode_id not in by_id:
            raise HTTPException(422, "Episode is not in this session's split.")
        try:
            _validate_review(review, by_id[review.episode_id], rubric, task)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        temp_path = None
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            # A file lock also protects two localhost processes using the same reviewer name.
            with out.with_suffix(".lock").open("a") as guard:
                fcntl.flock(guard, fcntl.LOCK_EX)
                saved = read_saved()
                previous = saved["reviews"].get(review.episode_id, {})
                if review.revision != previous.get("revision", 0):
                    raise HTTPException(409, "This review changed in another page. Copy your unsaved changes, then reload before editing again.")
                answer = review.model_dump()
                if answer["workflow"] == "manual":
                    del answer["workflow"]
                for judgment in answer["judgments"].values():
                    if judgment["assessment"] is None:
                        del judgment["assessment"]
                answer["elapsed_ms"] = max(answer["elapsed_ms"],
                    previous.get("elapsed_ms", 0))
                answer.update(revision=review.revision + 1, condition=conditions[review.episode_id],
                              saved_at=datetime.now(timezone.utc).isoformat())
                saved["reviews"][review.episode_id] = answer
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=out.parent,
                                                 suffix=".tmp", delete=False) as temporary:
                    temp_path = Path(temporary.name)
                    json.dump(saved, temporary, ensure_ascii=False, indent=2)
                    temporary.write("\n")
                    temporary.flush()
                    os.fsync(temporary.fileno())
                os.replace(temp_path, out)
            return {"review": answer}
        except (ValueError, TypeError) as error:
            raise HTTPException(409, f"Saved progress conflicts with this session: {error}") from error
        except OSError as error:
            raise HTTPException(503, f"Could not save progress: {error}. Keep this page open and retry.") from error
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Local episode review workspace")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--task", choices=["development", "coding", "comparison"], default="development")
    parser.add_argument("--split", choices=["development", "holdout"])
    parser.add_argument("--cohort", choices=[0, 1, 2], type=int, default=0)
    parser.add_argument("--port", type=int, default=8400)
    args = parser.parse_args()
    import uvicorn
    app = create_app(args.bundle, args.reviewer, args.task, args.cohort, args.split)
    print(f"Episode review: http://127.0.0.1:{args.port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
