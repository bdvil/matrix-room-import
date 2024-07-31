import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Generic, TypeVar, cast

from matrix_room_import import PROJECT_DIR
from matrix_room_import.config import Config

_T = TypeVar("_T")


class Store(Generic[_T], ABC):
    def __init__(self) -> None:
        super().__init__()
        self.data: dict[int, _T] = self.load_data()

    @abstractmethod
    def load_data(self) -> dict[int, _T]: ...

    def __contains__(self, x: int) -> bool:
        return x in self.data.keys()

    def has(self, x: _T) -> bool:
        return x in self.data.values()

    def __getitem__(self, x: int) -> _T:
        return self.data[x]

    def __len__(self) -> int:
        return len(self.data)

    @abstractmethod
    def append(self, data: _T) -> int: ...

    @abstractmethod
    def pop(self, x: int) -> _T: ...

    @abstractmethod
    def update(self, x: int, new_data: _T) -> None: ...


class DBStore(Store[_T]):
    def __init__(self, conninfo: PathLike):
        self.conninfo = conninfo
        super().__init__()

    def append(self, data: _T) -> int:
        row_id, row_data = self.insert_db(data)
        self.data[row_id] = row_data
        return row_id

    def pop(self, x: int) -> _T:
        if self.delete_db(x):
            out = self.data[x]
            del self.data[x]
            return out
        raise ValueError("Could not delete item")

    def update(self, x: int, new_data: _T) -> None:
        if self.update_db(x, new_data):
            self.data[x] = new_data
        raise ValueError("index does not exist")

    @abstractmethod
    def _load_data_query(self, cur: sqlite3.Cursor) -> sqlite3.Cursor: ...

    @abstractmethod
    def _extract_db_data(self, cur: sqlite3.Cursor) -> dict[int, _T]: ...

    @abstractmethod
    def _insert_data_query(self, cur: sqlite3.Cursor, data: _T) -> sqlite3.Cursor: ...

    @abstractmethod
    def _update_data_query(
        self, cur: sqlite3.Cursor, idx: int, data: _T
    ) -> sqlite3.Cursor: ...

    @abstractmethod
    def _delete_data_query(self, cur: sqlite3.Cursor, idx: int) -> sqlite3.Cursor: ...

    def load_data(self) -> dict[int, _T]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        data = self._load_data_query(cur)
        out = self._extract_db_data(data)
        conn.close()
        return out

    def insert_db(self, data: _T) -> tuple[int, _T]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        self._insert_data_query(cur, data)
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        if row_id is None:
            raise Exception("Could not insert into DB")
        return row_id, data

    def update_db(self, k: int, data: _T) -> bool:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        result = self._update_data_query(cur, k, data)
        conn.commit()
        row_count = result.rowcount
        conn.close()
        return row_count > 0

    def delete_db(self, data: int) -> bool:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        result = self._delete_data_query(cur, data)
        conn.commit()
        row_count = result.rowcount
        conn.close()
        return row_count > 0


class TXNStore(DBStore[str]):
    def _load_data_query(self, cur: sqlite3.Cursor) -> sqlite3.Cursor:
        return cur.execute("SELECT id, comment FROM transactions")

    def _extract_db_data(self, cur: sqlite3.Cursor) -> dict[int, str]:
        return {d[0]: d[1] for d in cur}

    def _insert_data_query(self, cur: sqlite3.Cursor, data: str) -> sqlite3.Cursor:
        return cur.execute("INSERT INTO transactions (comment) VALUES (?)", (data,))

    def _update_data_query(
        self, cur: sqlite3.Cursor, idx: int, data: str
    ) -> sqlite3.Cursor:
        raise NotImplementedError()

    def _delete_data_query(self, cur: sqlite3.Cursor, idx: int) -> sqlite3.Cursor:
        return cur.execute("DELETE FROM transations WHERE id=?", (idx,))

    def new_txn(self, comment: str) -> int:
        return self.append(comment)


class BotRoomsStore(DBStore[str]):
    def _load_data_query(self, cur: sqlite3.Cursor) -> sqlite3.Cursor:
        return cur.execute("SELECT id, room_id FROM bot_rooms")

    def _extract_db_data(self, cur: sqlite3.Cursor) -> dict[int, str]:
        return {d[0]: d[1] for d in cur}

    def _insert_data_query(self, cur: sqlite3.Cursor, data: str) -> sqlite3.Cursor:
        return cur.execute("INSERT INTO bot_rooms (room_id) VALUES (?)", (data,))

    def _update_data_query(
        self, cur: sqlite3.Cursor, idx: int, data: str
    ) -> sqlite3.Cursor:
        raise NotImplementedError()

    def _delete_data_query(self, cur: sqlite3.Cursor, idx: int) -> sqlite3.Cursor:
        return cur.execute("DELETE FROM bot_rooms WHERE id=?", (idx,))


@dataclass
class Process:
    path: Path
    event_id: str
    room_id: str


class QueueStore(DBStore[Process]):
    def _load_data_query(self, cur: sqlite3.Cursor) -> sqlite3.Cursor:
        return cur.execute("SELECT id, path, event_id, room_id FROM queue")

    def _extract_db_data(self, cur: sqlite3.Cursor) -> dict[int, Process]:
        return {
            d[0]: Process(path=Path(d[1]), event_id=d[2], room_id=d[3]) for d in cur
        }

    def _insert_data_query(self, cur: sqlite3.Cursor, data: Process) -> sqlite3.Cursor:
        return cur.execute(
            "INSERT INTO queue (path, event_id, room_id) VALUES (?, ?, ?)",
            (str(data.path.resolve()), data.event_id, data.room_id),
        )

    def _update_data_query(
        self, cur: sqlite3.Cursor, idx: int, data: Process
    ) -> sqlite3.Cursor:
        raise NotImplementedError()

    def _delete_data_query(self, cur: sqlite3.Cursor, idx: int) -> sqlite3.Cursor:
        return cur.execute("DELETE FROM queue WHERE id=?", (idx,))

    def get_and_remove_next(self) -> Process:
        k = next(iter(self.data.keys()))
        return self.pop(k)


@dataclass
class RoomEvent:
    event_id: str
    room_id: str
    users: list[str]


class RoomsToRemoveStore(DBStore[RoomEvent]):
    def _load_data_query(self, cur: sqlite3.Cursor) -> sqlite3.Cursor:
        return cur.execute(
            "SELECT id, event_id, room_id, userlist FROM rooms_to_remove"
        )

    def _extract_db_data(self, cur: sqlite3.Cursor) -> dict[int, RoomEvent]:
        return {
            d[0]: RoomEvent(d[1], d[2], d[3].split(",") if d[3] != "" else [])
            for d in cur
        }

    def _insert_data_query(
        self, cur: sqlite3.Cursor, data: RoomEvent
    ) -> sqlite3.Cursor:
        return cur.execute(
            "INSERT INTO rooms_to_remove (event_id, room_id, userlist) VALUES (?, ?, ?)",
            (data.event_id, data.room_id, ",".join(data.users)),
        )

    def _update_data_query(
        self, cur: sqlite3.Cursor, idx: int, data: RoomEvent
    ) -> sqlite3.Cursor:
        raise NotImplementedError()

    def _delete_data_query(self, cur: sqlite3.Cursor, idx: int) -> sqlite3.Cursor:
        return cur.execute("DELETE FROM rooms_to_remove WHERE id=?", (idx,))

    def has_event(self, event_id: str) -> bool:
        for event in self.data.values():
            if event.event_id == event_id:
                return True
        return False

    def has_room_id(self, room_id: str) -> bool:
        for event in self.data.values():
            if event.room_id == room_id:
                return True
        return False

    def get_room_id(self, event_id: str) -> str:
        for event in self.data.values():
            if event.event_id == event_id:
                return event.room_id
        raise ValueError("event_id not in db")

    def get_users(self, event_id: str) -> list[str]:
        for event in self.data.values():
            if event.event_id == event_id:
                return event.users
        raise ValueError("event_id not in db")

    def pop_from_event(self, event_id: str) -> RoomEvent:
        for k, event in self.data.items():
            if event.event_id == event_id:
                return self.pop(k)
        raise ValueError("event_id not in db")


@dataclass
class ConfigEntry:
    key: str
    value: str | None


class ConfigStore(DBStore[ConfigEntry]):
    def _load_data_query(self, cur: sqlite3.Cursor) -> sqlite3.Cursor:
        return cur.execute("SELECT id, key, value FROM config")

    def _extract_db_data(self, cur: sqlite3.Cursor) -> dict[int, ConfigEntry]:
        return {d[0]: ConfigEntry(d[1], d[2]) for d in cur}

    def _insert_data_query(
        self, cur: sqlite3.Cursor, data: ConfigEntry
    ) -> sqlite3.Cursor:
        return cur.execute(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            (data.key, data.value),
        )

    def _update_data_query(
        self, cur: sqlite3.Cursor, idx: int, data: ConfigEntry
    ) -> sqlite3.Cursor:
        return cur.execute(
            "UPDATE config SET key=?, value=? WHERE id=?",
            (data.key, data.value, idx),
        )

    def _delete_data_query(self, cur: sqlite3.Cursor, idx: int) -> sqlite3.Cursor:
        return cur.execute("DELETE FROM config WHERE id=?", (idx,))

    def from_key(self, key: str) -> str | None:
        for config in self.data.values():
            if config.key == key:
                return config.value
        raise ValueError("key not in config")

    def update_key(self, key: str, value: str | None) -> bool:
        for k, config in self.data.items():
            if config.key == key:
                return self.update_db(k, ConfigEntry(config.key, value))
        raise ValueError("key not in db")


stores: dict[str, Store] = {}


def get_txn_store(config: Config) -> TXNStore:
    if "txn" not in stores:
        stores["txn"] = TXNStore(PROJECT_DIR / config.database_location)
    return cast(TXNStore, stores["txn"])


def get_bot_rooms_store(config: Config) -> BotRoomsStore:
    if "bot_rooms" not in stores:
        stores["bot_rooms"] = BotRoomsStore(PROJECT_DIR / config.database_location)
    return cast(BotRoomsStore, stores["bot_rooms"])


def get_queue_store(config: Config) -> QueueStore:
    if "queue" not in stores:
        stores["queue"] = QueueStore(PROJECT_DIR / config.database_location)
    return cast(QueueStore, stores["queue"])


def get_rooms_to_remove_store(config: Config) -> RoomsToRemoveStore:
    if "rooms_to_remove" not in stores:
        stores["rooms_to_remove"] = RoomsToRemoveStore(
            PROJECT_DIR / config.database_location
        )
    return cast(RoomsToRemoveStore, stores["rooms_to_remove"])


def get_config_store(config: Config) -> ConfigStore:
    if "config" not in stores:
        stores["config"] = ConfigStore(PROJECT_DIR / config.database_location)
    return cast(ConfigStore, stores["config"])
