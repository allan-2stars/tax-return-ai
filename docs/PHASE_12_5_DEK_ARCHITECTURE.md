# Phase 12.5: DEK + Wrapped-Key Architecture

## Key Hierarchy
- DEK (Data Encryption Key)
  - random stable 256-bit key
  - encrypts sensitive fields and encrypted workflow payloads
- Password KEK
  - derived from master password
  - wraps DEK
- Recovery KEK
  - derived from recovery key
  - wraps same DEK

Text diagram:
Master Password -> Password KEK -> wraps DEK
Recovery Key    -> Recovery KEK -> wraps same DEK
DEK -> encrypt/decrypt sensitive data

## DEK Lifecycle
- Setup:
  - generate random DEK
  - wrap DEK by password KEK and recovery KEK
  - store wrapped forms and metadata only
- Unlock:
  - derive password KEK, unwrap DEK
  - cache DEK in-memory per auth session
- Logout/session expiry:
  - clear DEK cache entry

## Password Reset Behavior
- Recovery reset flow:
  - verify recovery key
  - unwrap DEK with recovery KEK
  - set new password and derive new password KEK
  - rewrap same DEK (no bulk data re-encryption)
- Old password becomes invalid.
- Encrypted data remains accessible with new password.

## Recovery Behavior
- Recovery key is now a real data-access recovery mechanism.
- Recovery key can restore access and establish a new password.
- Losing both password and recovery key means permanent data loss.

## Migration Strategy
- Existing users without wrapped DEK are supported:
  - on unlock, bootstrap wrapped password DEK from legacy key derivation
  - mark as legacy-compatible DEK version metadata
- Existing encrypted rows remain readable.
- Field encryption/decryption now uses cached DEK.

## Remaining Risks
- Recovery reset requires `encrypted_dek_by_recovery` availability for older accounts.
- In-memory DEK cache remains process-local.
- Plaintext legacy columns still exist during migration period.

## Future Rotation
- Add DEK rotation workflow with staged rewrap/re-encrypt.
- Add shared ephemeral key broker for multi-process worker deployments.
