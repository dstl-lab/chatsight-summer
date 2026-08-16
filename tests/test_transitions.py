import json
import sys

from src.trajectories.transitions import (END_STATE, NO_LABEL_FITS_STATE,
                                          NO_LABEL_STATE,
                                          build_transition_matrix,
                                          default_output_path,
                                          main)


def _trajectory_report() -> dict:
    return {
        "metadata": {
            "snapshot_id": "snap1",
            "schema_version": "schema123",
            "classifier_hash": "hash123",
            "repo_sha": "abc",
            "label_names": ["confused", "asks-answer"],
            "row_counts": {
                "conversations": 2,
                "trajectories": 2,
                "steps": 4,
            },
        },
        "trajectories": [
            {
                "conv_id": "a",
                "chatlog_id": 1,
                "steps": [
                    {"active_labels": ["confused"], "no_label_fits": False},
                    {"active_labels": ["asks-answer"], "no_label_fits": False},
                    {"active_labels": [], "no_label_fits": True},
                ],
            },
            {
                "conv_id": "b",
                "chatlog_id": 2,
                "steps": [
                    {"active_labels": [], "no_label_fits": False},
                ],
            },
        ],
    }


def test_transition_matrix_counts_probabilities_and_terminal_state():
    report = build_transition_matrix(_trajectory_report())

    assert report["metadata"]["snapshot_id"] == "snap1"
    assert report["metadata"]["schema_version"] == "schema123"
    assert report["metadata"]["classifier_hash"] == "hash123"
    assert report["metadata"]["artifact_type"] == "empirical_transition_matrix"
    assert report["metadata"]["source_row_counts"] == {
        "conversations": 2,
        "trajectories": 2,
        "steps": 4,
    }
    assert report["metadata"]["terminal_state"] == END_STATE
    assert report["metadata"]["row_counts"] == {
        "trajectories": 2,
        "steps": 4,
        "states": 5,
        "transitions": 4,
    }

    assert report["transition_counts"] == {
        "asks-answer": {NO_LABEL_FITS_STATE: 1},
        "confused": {"asks-answer": 1},
        NO_LABEL_FITS_STATE: {END_STATE: 1},
        NO_LABEL_STATE: {END_STATE: 1},
    }
    assert report["transition_probabilities"] == {
        "asks-answer": {NO_LABEL_FITS_STATE: 1.0},
        "confused": {"asks-answer": 1.0},
        NO_LABEL_FITS_STATE: {END_STATE: 1.0},
        NO_LABEL_STATE: {END_STATE: 1.0},
    }
    assert report["states"][END_STATE]["terminal"] is True
    assert report["states"][NO_LABEL_STATE]["active_labels"] == []
    assert report["states"][NO_LABEL_FITS_STATE]["no_label_fits"] is True
    assert report["sequences"] == [
        {
            "conv_id": "a",
            "chatlog_id": 1,
            "states": [
                "confused",
                "asks-answer",
                NO_LABEL_FITS_STATE,
                END_STATE,
            ],
        },
        {
            "conv_id": "b",
            "chatlog_id": 2,
            "states": [NO_LABEL_STATE, END_STATE],
        },
    ]


def test_state_ids_follow_schema_label_order():
    report = _trajectory_report()
    report["trajectories"][0]["steps"][0]["active_labels"] = [
        "asks-answer", "confused"]

    matrix = build_transition_matrix(report)

    assert "confused+asks-answer" in matrix["states"]


def test_transition_matrix_omits_student_text_and_rationales():
    source = _trajectory_report()
    source["trajectories"][0]["steps"][0]["text"] = "student secret"
    source["trajectories"][0]["steps"][0]["rationale"] = "model reason"

    rendered = json.dumps(build_transition_matrix(source))

    assert "student secret" not in rendered
    assert "model reason" not in rendered


def test_cli_writes_requested_output(tmp_path, monkeypatch, capsys):
    trajectory_json = tmp_path / "trajectories.json"
    out = tmp_path / "transition-matrix.json"
    trajectory_json.write_text(json.dumps(_trajectory_report()))
    monkeypatch.setattr(sys, "argv", [
        "transition-matrix", str(trajectory_json), "--out", str(out)])

    main()

    saved = json.loads(out.read_text())
    assert saved["metadata"]["artifact_type"] == "empirical_transition_matrix"
    assert "wrote" in capsys.readouterr().out


def test_default_output_path_sits_next_to_trajectories_file(tmp_path):
    trajectory_json = tmp_path / "data" / "trajectories" / "snap1" / \
        "trajectories.json"

    assert default_output_path(trajectory_json) == \
        tmp_path / "data" / "trajectories" / "snap1" / \
        "transition-matrix.json"
