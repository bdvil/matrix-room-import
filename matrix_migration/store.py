from abc import ABC, abstractmethod
from typing import Generic, TypeVar

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
