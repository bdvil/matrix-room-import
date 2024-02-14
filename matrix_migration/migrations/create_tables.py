from psycopg import AsyncConnection


async def create_tables_migration(conninfo: str):
    async with await AsyncConnection.connect(conninfo) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
CREATE TABLE migrations (
    id serial PRIMARY KEY,
    name varchar(255)
)
"""
            )
            await cur.execute(
                """
CREATE TABLE bot_infos (
    id serial PRIMARY KEY,
    key varchar(255)
    value varchar(255)
)
"""
            )

            await cur.execute(
                """
CREATE TABLE transactions (
    id serial PRIMARY KEY,
    endpoint varchar(255),
    method varchar(10),
    response text
)
"""
            )
            await conn.commit()
