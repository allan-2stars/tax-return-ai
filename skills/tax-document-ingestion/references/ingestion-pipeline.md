# Document Ingestion Pipeline Reference

The ingestion layer must be deterministic, auditable, and conservative.

## Default Pipeline

1. Store original file.
2. Create SHA-256 hash.
3. Extract text layer.
4. Use OCR only when needed.
5. Normalise candidate fields.
6. Detect duplicate/near-duplicate documents.
7. Save raw extraction and normalised output.
8. Hand off to classification.

## Design Principle

Never lose source evidence. The product must be able to show users where each extracted value came from.
