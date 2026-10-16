"""The Alembic migrations, not just the ORM models, must produce a working schema."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    return config


def table_names(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_migrations_upgrade_and_downgrade(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'migrations.db'}"
    config = alembic_config(url)

    command.upgrade(config, "head")
    assert {"rooms", "reservations", "alembic_version"} <= table_names(url)
    engine = create_engine(url)
    columns = {column["name"] for column in inspect(engine).get_columns("reservations")}
    engine.dispose()
    assert {"room_id", "check_in", "check_out", "status", "total_amount"} <= columns

    command.downgrade(config, "base")
    assert table_names(url) == {"alembic_version"}
