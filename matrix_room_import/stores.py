import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Generic, TypeVar, cast

from matrix_room_import import PROJECT_DIR
from matrix_room_import.config import Config

_T = TypeVar("_T")
_U = TypeVar("_U")


class Store(Generic[_T, _U], ABC):
    def __init__(self) -> None:
        super().__init__()
        self.data: dict[_T, _U] = self.load_data()

    @abstractmethod
    def load_data(self) -> dict[_T, _U]: ...

    def __contains__(self, x: _T) -> bool:
        return x in self.data.keys()

    def has(self, x: _U) -> bool:
        return x in self.data.values()

    def __getitem__(self, x: _T) -> _U:
        return self.data[x]

    def __len__(self) -> int:
        return len(self.data)

    @abstractmethod
    def append(self, data: _U) -> _T: ...

    @abstractmethod
    def pop(self, x: _T) -> _U: ...


class DBStore(Store[_T, _U], ABC):
    @abstractmethod
    def insert_db(self, data: _U) -> tuple[_T, _U]: ...

    @abstractmethod
    def delete_db(self, data: _T) -> bool: ...

    def append(self, data: _U) -> _T:
        row_id, row_data = self.insert_db(data)
        self.data[row_id] = row_data
        return row_id

    def pop(self, x: _T) -> _U:
        if self.delete_db(x):
            out = self.data[x]
            del self.data[x]
            return out
        raise ValueError("Could not delete item")


class TXNStore(DBStore[int, str]):
    def __init__(self, conninfo: PathLike) -> None:
        self.conninfo = conninfo
        super().__init__()

    def load_data(self) -> dict[int, str]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        data = cur.execute("SELECT id, comment FROM transactions")
        out = {d[0]: d[1] for d in data}
        conn.close()
        return out

    def insert_db(self, data: str) -> tuple[int, str]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        cur.execute("INSERT INTO transactions (comment) VALUES (?)", (data,))
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        if row_id is None:
            raise Exception("Could not insert into DB")
        return row_id, data

    def delete_db(self, data: int) -> bool:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        result = cur.execute("DELETE FROM transations WHERE id=?", (data,))
        conn.commit()
        row_count = result.rowcount
        conn.close()
        return row_count > 0

    def new_txn(self, comment: str) -> int:
        return self.append(comment)


class BotRoomsStore(DBStore[int, str]):
    def __init__(self, conninfo: PathLike) -> None:
        self.conninfo = conninfo
        super().__init__()

    def load_data(self) -> dict[int, str]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        data = cur.execute("SELECT id, room_id FROM bot_rooms")
        out = {d[0]: d[1] for d in data}
        conn.close()
        return out

    def insert_db(self, data: str) -> tuple[int, str]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        cur.execute("INSERT INTO bot_rooms (room_id) VALUES (?)", (data,))
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        if row_id is None:
            raise Exception("Could not insert into DB")
        return row_id, data

    def delete_db(self, data: int) -> bool:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        result = cur.execute("DELETE FROM bot_rooms WHERE id=?", (data,))
        conn.commit()
        row_count = result.rowcount
        conn.close()
        return row_count > 0


@dataclass
class Process:
    path: Path
    event_id: str
    room_id: str


class QueueStore(DBStore[int, Process]):
    def __init__(self, conninfo: PathLike) -> None:
        self.conninfo = conninfo
        super().__init__()

    def load_data(self) -> dict[int, Process]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        data = cur.execute("SELECT id, path, event_id, room_id FROM queue")
        out = {
            d[0]: Process(path=Path(d[1]), event_id=d[2], room_id=d[3]) for d in data
        }
        conn.close()
        return out

    def insert_db(self, data: Process) -> tuple[int, Process]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queue (path, event_id, room_id) VALUES (?, ?, ?)",
            (str(data.path.resolve()), data.event_id, data.room_id),
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        if row_id is None:
            raise Exception("Could not insert into DB")
        return row_id, data

    def delete_db(self, data: int) -> bool:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        result = cur.execute("DELETE FROM queue WHERE id=?", (data,))
        conn.commit()
        row_count = result.rowcount
        conn.close()
        return row_count > 0

    def get_and_remove_next(self) -> Process:
        k = next(iter(self.data.keys()))
        return self.pop(k)


@dataclass
class RoomEvent:
    event_id: str
    room_id: str


class RoomsToRemoveStore(DBStore[int, RoomEvent]):
    def __init__(self, conninfo: PathLike) -> None:
        self.conninfo = conninfo
        super().__init__()

    def load_data(self) -> dict[int, RoomEvent]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        data = cur.execute("SELECT id, event_id, room_id FROM rooms_to_remove")
        out = {d[0]: RoomEvent(d[1], d[2]) for d in data}
        conn.close()
        return out

    def insert_db(self, data: RoomEvent) -> tuple[int, RoomEvent]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO rooms_to_remove (event_id, room_id) VALUES (?, ?)",
            (data.event_id, data.room_id),
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        if row_id is None:
            raise Exception("Could not insert into DB")
        return row_id, data

    def delete_db(self, data: int) -> bool:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        result = cur.execute("DELETE FROM rooms_to_remove WHERE id=?", (data,))
        conn.commit()
        row_count = result.rowcount
        conn.close()
        return row_count > 0

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

    def pop_from_event(self, event_id: str) -> RoomEvent:
        for k, event in self.data.items():
            if event.event_id == event_id:
                return self.pop(k)
        raise ValueError("event_id not in db")


@dataclass
class ConfigEntry:
    key: str
    value: str | None


class ConfigStore(DBStore[int, ConfigEntry]):
    def __init__(self, conninfo: PathLike) -> None:
        self.conninfo = conninfo
        super().__init__()

    def load_data(self) -> dict[int, ConfigEntry]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        data = cur.execute("SELECT id, key, value FROM config")
        out = {d[0]: ConfigEntry(d[1], d[2]) for d in data}
        conn.close()
        return out

    def insert_db(self, data: ConfigEntry) -> tuple[int, ConfigEntry]:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            (data.key, data.value),
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        if row_id is None:
            raise Exception("Could not insert into DB")
        return row_id, data

    def update_db(self, k: int, data: ConfigEntry) -> bool:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        result = cur.execute(
            "UPDATE config SET key=?, value=? WHERE id=?",
            (data.key, data.value, k),
        )
        conn.commit()
        row_count = result.rowcount
        conn.close()
        return row_count > 0

    def delete_db(self, data: int) -> bool:
        conn = sqlite3.connect(self.conninfo)
        cur = conn.cursor()
        result = cur.execute("DELETE FROM rooms_to_remove WHERE id=?", (data,))
        conn.commit()
        row_count = result.rowcount
        conn.close()
        return row_count > 0

    def from_key(self, key: str) -> str | None:
        for config in self.data.values():
            if config.key == key:
                return config.value
        raise ValueError("key not in config")

    def update_key(self, key: str, value: str) -> bool:
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
