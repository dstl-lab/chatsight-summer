import json

import pytest

from src.ingest.episode_events import build_dataset
from src.viewer.briefing import load_cached_briefing
from src.viewer.classification import load_cached_classifications
from src.viewer.demo import DEMO_DIR, DEMO_EVENTS, main
from src.viewer.overview import load_cached_overview


def test_committed_demo_is_complete_and_ready_to_view():
    manifest = json.loads((DEMO_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert manifest["generation"]["student_count"] == 100
    assert manifest["generation"]["question_count"] == 8
    assert set(manifest["files"]) == {
        "events",
        "cohort_summary",
        "classifications",
        "overview",
        "briefing",
        "validation_report",
        "instructions",
    }

    dataset = build_dataset(DEMO_EVENTS, source_kind="synthetic")
    classifications = load_cached_classifications(
        DEMO_DIR / "classifications.json", dataset
    )
    assert classifications is not None
    assert load_cached_overview(
        DEMO_DIR / "overview.json", dataset, classifications
    ) is not None
    assert load_cached_briefing(
        DEMO_DIR / "briefing.json", dataset, classifications
    ) is not None


def test_demo_help_only_exposes_the_optional_port(capsys):
    with pytest.raises(SystemExit, match="0"):
        main(["--help"])
    help_text = capsys.readouterr().out
    assert "episode-viewer-demo [-h] [--port PORT]" in help_text
    assert "--input" not in help_text
