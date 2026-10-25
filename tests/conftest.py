import json

import pytest

from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / "data"
VERIFIED_DIR = TESTS_DIR / "verified"


@pytest.fixture
def data():

    def get(name):
        path = DATA_DIR / name
        assert path.exists(), f"нет входного файла {path}"
        return str(path)

    return get


@pytest.fixture
def expected():

    def get(name):
        text = (VERIFIED_DIR / f"{name}.json").read_text(encoding="utf-8")
        return json.loads(text)

    return get
