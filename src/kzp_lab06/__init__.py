"""Звіт аптеки з CSV-файла (КЗП, ЛР6, варіант 11)."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Версія береться з метаданих встановленого пакета, тобто з project.version у pyproject.toml.
    __version__ = version("kzp-lab06")
except PackageNotFoundError:  # пакет запущено з вихідних кодів без встановлення
    __version__ = "0+unknown"
