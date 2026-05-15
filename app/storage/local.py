"""Local filesystem storage backend."""
import aiofiles
from pathlib import Path
from app.storage.base import StorageBackend
from app.config import settings


class LocalStorage(StorageBackend):
    def __init__(self) -> None:
        self.root = Path(settings.storage_local_path)
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return str(path.relative_to(self.root))

    async def get(self, storage_path: str) -> bytes:
        async with aiofiles.open(self.root / storage_path, "rb") as f:
            return await f.read()

    async def delete(self, storage_path: str) -> None:
        (self.root / storage_path).unlink(missing_ok=True)

    async def exists(self, storage_path: str) -> bool:
        return (self.root / storage_path).exists()
