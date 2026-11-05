import hashlib
import hmac
import secrets

DEFAULT_PASSWORD = "123456"
_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, expected_hex = stored_hash.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return hmac.compare_digest(digest.hex(), expected_hex)


def default_password_hash() -> str:
    return hash_password(DEFAULT_PASSWORD)
