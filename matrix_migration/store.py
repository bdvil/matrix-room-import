from abc import ABC, abstractmethod
from typing import Any


class Store(ABC):
    @abstractmethod
    def append(self, content: Any) -> None: ...

    @abstractmethod
    def __contains__(self, value: Any) -> bool: ...

    @abstractmethod
    def __getitem__(self, value: Any) -> Any: ...


class RAMStore(Store):
    def __init__(self):
        self._storage = []

    def append(self, content: Any) -> None:
        self._storage.append(content)

    def __contains__(self, value: Any) -> bool:
        return value in self._storage

    def __getitem__(self, value: int) -> Any:
        return self._storage[value]
