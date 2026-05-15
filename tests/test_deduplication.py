"""Deduplication service tests."""
from app.services.ingestion.deduplication import compute_file_hash


def test_hash_is_sha256():
    h = compute_file_hash(b"test data")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_same_bytes_same_hash():
    assert compute_file_hash(b"hello") == compute_file_hash(b"hello")


def test_different_bytes_different_hash():
    assert compute_file_hash(b"hello") != compute_file_hash(b"world")
