"""S3-compatible storage backend stub."""
from app.storage.base import StorageBackend


class S3Storage(StorageBackend):
    async def save(self, key: str, data: bytes, content_type: str) -> str:
        raise NotImplementedError("S3Storage not yet implemented")

    async def get(self, path: str) -> bytes:
        raise NotImplementedError

    async def delete(self, path: str) -> None:
        raise NotImplementedError

    async def exists(self, path: str) -> bool:
        raise NotImplementedError
