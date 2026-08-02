import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    ext_db_url: str
    gemini_api_key: str | None
    repo_root: Path
    data_dir: Path

    @classmethod
    def load(cls, dotenv: bool = True) -> "Settings":
        if dotenv:
            load_dotenv(_REPO_ROOT / ".env")
        ext_db_url = os.environ.get("EXT_DB_URL")
        if not ext_db_url:
            pg_password = os.environ["PG_PASSWORD"]
            ext_db_url = (
                f"postgresql+psycopg2://dsc10_tutor:{pg_password}"
                "@localhost:5432/dsc10_tutor_logs"
            )
        return cls(
            ext_db_url=ext_db_url,
            gemini_api_key=os.environ.get("GEMINI_API_KEY"),
            repo_root=_REPO_ROOT,
            data_dir=_REPO_ROOT / "data",
        )
