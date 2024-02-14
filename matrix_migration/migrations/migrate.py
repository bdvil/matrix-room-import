from collections.abc import Callable, Coroutine
from typing import Any

from psycopg import AsyncConnection

from matrix_migration import LOGGER

from .create_tables import create_tables_migration

migration_order: list[tuple[str, Callable[[str], Coroutine[Any, Any, None]]]] = [
    ("0_create_tables", create_tables_migration),
]


async def check_done_migrations(conninfo: str) -> list[str]:
    async with await AsyncConnection.connect(conninfo) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'migrations'
)
"""
            )
            record = await cur.fetchone()
            LOGGER.debug(record)
            if record is None or record is False:
                return []

            await cur.execute("SELECT name FROM migrations")
            names: list[str] = []
            async for record in cur:
                LOGGER.debug(record)
                names.append(record[0])
            return names


async def update_migration_table(conninfo: str, migration_name: str):
    async with await AsyncConnection.connect(conninfo) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO migrations (name) VALUES (%s)", (migration_name,)
            )
            await conn.commit()


async def execute_migration(conninfo: str):
    done_migrations = await check_done_migrations(conninfo)
    LOGGER.debug(f"Done migrations: {done_migrations}")
    for migration_name, migration in migration_order:
        if migration_name in done_migrations:
            continue

        LOGGER.info(f"Executing migration {migration_name}")
        await migration(conninfo)
        await update_migration_table(conninfo, migration_name)
