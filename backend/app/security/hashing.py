"""Password and Green PIN hashing.

Argon2id is used for both. Plaintext is never stored, never logged and never
returned by an API. Verification is constant-time by construction.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type

#: Interactive parameters: ~64 MiB and 3 passes. Comfortably above the OWASP
#: minimum while keeping a login under roughly 100 ms on small hardware.
_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

#: A 4-digit PIN has only 10,000 combinations, so an offline attacker with the
#: hash could brute-force any parameter set. Cost is raised here and, far more
#: importantly, online attempts are rate limited and locked out.
_pin_hasher = PasswordHasher(
    time_cost=4,
    memory_cost=98304,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return False


def hash_pin(pin: str) -> str:
    return _pin_hasher.hash(pin)


def verify_pin(pin: str, pin_hash: str | None) -> bool:
    if not pin_hash:
        return False
    try:
        return _pin_hasher.verify(pin_hash, pin)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def dummy_verify() -> None:
    """Burn a comparable amount of CPU when an account does not exist.

    Without this, a fast 404-style response would tell an attacker which
    e-mail addresses are registered.
    """
    try:
        _password_hasher.verify(
            "$argon2id$v=19$m=65536,t=3,p=2$c29tZXNhbHRzb21lc2E$"
            "3a5PZTuqQGZ7ZzTKmZAcVQK0Xz4Hxs5cGGmL2gMLvXk",
            "not-the-password",
        )
    except Exception:
        pass
