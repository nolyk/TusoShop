"""Never log mnemonic input or persist it in FSM. Encryption key lives outside DB."""
import os

from cryptography.fernet import Fernet


def wallet_cipher() -> Fernet:
    key = os.environ.get("WALLET_ENCRYPTION_KEY", "")
    if not key:
        raise ValueError("Wallet encryption is not configured")
    return Fernet(key.encode("ascii"))


def encrypt_mnemonic(value: str) -> str:
    from tonsdk.crypto import mnemonic_is_valid

    words = value.strip().lower().split()
    if len(words) != 24 or not mnemonic_is_valid(words):
        raise ValueError("Invalid TON mnemonic")
    return wallet_cipher().encrypt(" ".join(words).encode("ascii")).decode("ascii")
