from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from psycopg import AsyncConnection

from matrix_migration import LOGGER

T = TypeVar("T")


class Store(ABC, Generic[T]):
    @abstractmethod
    def append(self, content: T) -> None: ...

    @abstractmethod
    def __contains__(self, value: T) -> bool: ...

    @abstractmethod
    def __getitem__(self, value: T) -> T: ...


class RAMStore(Store, Generic[T]):
    def __init__(self):
        self._storage: list[T] = []

    def append(self, content: T) -> None:
        self._storage.append(content)

    def __contains__(self, value: T) -> bool:
        return value in self._storage

    def __getitem__(self, value: int) -> T:
        return self._storage[value]


class BotInfos:
    async def __init__(self, conninfo: str):
        self.conninfo = conninfo

        self._device_id: str | None = None
        self._access_token: str | None = None

        await self._get_fields()

    async def _get_fields(self):
        async with await AsyncConnection.connect(self.conninfo) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT key, value FROM bot_infos")
                async for record in cur:
                    match record[0]:
                        case "device_id":
                            LOGGER.debug(f"device_id {record[1]}")
                            self._device_id = record[1]
                        case "access_token":
                            LOGGER.debug(f"access_token {record[1]}")
                            self._access_token = record[1]

    async def _set_key(self, key: str, value: str):
        async with await AsyncConnection.connect(self.conninfo) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO bot_infos (key, value) SET (%s, %s)",
                    (key, value),
                )
                await conn.commit()

    @property
    def device_id(self):
        return self._device_id

    @property
    def access_token(self):
        return self._access_token

    @device_id.setter
    async def device_id(self, device_id: str):
        await self._set_key("device_id", device_id)
        self._device_id = device_id

    @access_token.setter
    async def access_token(self, access_token: str):
        await self._set_key("access_token", access_token)
        self._access_token = access_token
