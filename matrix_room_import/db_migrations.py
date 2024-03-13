import sqlite3
from os import PathLike
from pathlib import Path

from matrix_room_import import LOGGER, PROJECT_DIR


def migration_order() -> list[Path]:
    migration_dir = PROJECT_DIR / "migrations"
    migrations: list[Path] = []
    for file in migration_dir.iterdir():
        if not file.is_file() and file.suffix != ".sql":
            continue
        migrations.append(file)
    return sorted(migrations, key=lambda x: x.stem)


def check_done_migrations(conninfo: PathLike) -> list[str]:
    conn = sqlite3.connect(conninfo)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
    )
    record = cur.fetchone()
    if record is None or record[0] is False:
        return []

    cur.execute("SELECT name FROM migrations")
    names: list[str] = []
    for record in cur:
        names.append(record[0])
    return names


def update_migration_table(conninfo: PathLike, migration_name: str):
    conn = sqlite3.connect(conninfo)
    cur = conn.cursor()
    cur.execute("INSERT INTO migrations (name) VALUES (?)", (migration_name,))
    conn.commit()


def execute_migration(conninfo: PathLike, migration: Path):
    if not migration.is_file() and migration.suffix != ".sql":
        return

    conn = sqlite3.connect(conninfo)
    cur = conn.cursor()
    with open(migration, "rb") as f:
        cur.executescript(f.read().decode())
    conn.commit()


def execute_migrations(conninfo: PathLike):
    done_migrations = check_done_migrations(conninfo)
    LOGGER.debug(f"Done migrations: {done_migrations}")
    for migration in migration_order():
        if migration.stem in done_migrations:
            continue

        LOGGER.info(f"Executing migration {migration.stem}")
        execute_migration(conninfo, migration)
        update_migration_table(conninfo, migration.stem)
