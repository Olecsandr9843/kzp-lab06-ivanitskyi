"""Об'єктно-орієнтований звіт аптеки з CSV (КЗП, ЛР7, варіант 11)."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Версія з метаданих встановленого дистрибутива (project.version у pyproject.toml).
    __version__ = version("kzp-pharmacy")
except PackageNotFoundError:  # запуск із вихідних кодів без встановлення
    __version__ = "0+unknown"
