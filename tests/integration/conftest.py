from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import get_settings


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    repository_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(repository_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(repository_root / "alembic"))
    alembic_config.config_file_name = None
    command.upgrade(alembic_config, "head")

    engine = create_engine(get_settings().database_url_resolvida)
    yield engine
    engine.dispose()
