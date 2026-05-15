"""Storage backend ABC. All file I/O goes through this — never use open() or boto3 in services."""
from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes, content_type: str) -> str:
        """Persist data. Return opaque storage path."""

    @abstractmethod
    async def get(self, path: str) -> bytes:
        """Retrieve data by storage path."""

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete data at storage path."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Return True if the path exists."""
