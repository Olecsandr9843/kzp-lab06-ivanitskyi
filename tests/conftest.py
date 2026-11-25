"""Спільні фікстури тестів."""

from pathlib import Path

import pytest

HEADER = "name,form,price,days_left,prescription\n"


@pytest.fixture
def write_csv(tmp_path: Path):
    """Повертає функцію, що записує CSV у тимчасовий каталог і повертає шлях до нього."""

    def _write(body: str, header: str = HEADER, name: str = "input.csv") -> Path:
        path = tmp_path / name
        path.write_text(header + body, encoding="utf-8", newline="")
        return path

    return _write


@pytest.fixture
def sample_path() -> Path:
    """Шлях до контрольного файла data/input.csv (тести запускаються з кореня проєкту)."""
    return Path(__file__).resolve().parent.parent / "data" / "input.csv"
