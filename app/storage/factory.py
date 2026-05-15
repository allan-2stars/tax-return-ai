"""Return the configured storage backend. Never instantiate backends outside this factory."""
from app.storage.base import StorageBackend
from app.config import settings


def get_storage_backend() -> StorageBackend:
    backend = settings.storage_backend.lower()
    if backend == "local":
        from app.storage.local import LocalStorage
        return LocalStorage()
    if backend == "s3":
        from app.storage.s3 import S3Storage
        return S3Storage()
    raise ValueError(f"Unknown STORAGE_BACKEND: {backend!r}")
