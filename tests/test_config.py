from pathlib import Path
from src.config import Settings


def test_default_ext_db_url_built_from_pg_password(monkeypatch):
    monkeypatch.setenv("PG_PASSWORD", "sekrit")
    monkeypatch.delenv("EXT_DB_URL", raising=False)
    s = Settings.load(dotenv=False)
    assert s.ext_db_url == (
        "postgresql+psycopg2://dsc10_tutor:sekrit@localhost:5432/dsc10_tutor_logs"
    )


def test_ext_db_url_env_override_wins(monkeypatch):
    monkeypatch.setenv("PG_PASSWORD", "ignored")
    monkeypatch.setenv("EXT_DB_URL", "postgresql+psycopg2://u:p@h:5/db")
    assert Settings.load(dotenv=False).ext_db_url == "postgresql+psycopg2://u:p@h:5/db"


def test_data_dir_is_repo_data(monkeypatch):
    monkeypatch.setenv("PG_PASSWORD", "x")
    s = Settings.load(dotenv=False)
    assert s.data_dir == s.repo_root / "data"
    assert (s.repo_root / "CLAUDE.md").exists()


def test_labeling_workers_default_and_env(monkeypatch):
    monkeypatch.setenv("EXT_DB_URL", "postgresql://x/y")
    monkeypatch.delenv("LABELING_WORKERS", raising=False)
    assert Settings.load(dotenv=False).labeling_workers == 8
    monkeypatch.setenv("LABELING_WORKERS", "2")
    assert Settings.load(dotenv=False).labeling_workers == 2
