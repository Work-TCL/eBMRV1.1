import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.db import connect, migrate  # noqa: E402


@pytest.fixture()
def conn(tmp_path):
    connection = connect(tmp_path / "edge.db")
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "edge.db"