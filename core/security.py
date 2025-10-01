from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


class SecretCipher:
    def __init__(self, key: str | bytes):
        if isinstance(key, str):
            key = key.encode()
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:  # pragma: no cover - defensive
            raise ValueError("Invalid secret token") from exc


cipher = SecretCipher(settings.secrets_key)
