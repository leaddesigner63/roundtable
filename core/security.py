from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


class SecretsCipher:
    def __init__(self, key: str):
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Invalid secret token") from exc


cipher = SecretsCipher(settings.secrets_key)
