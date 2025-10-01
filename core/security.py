from cryptography.fernet import Fernet, InvalidToken
from typing import Optional

from core.config import get_settings


class SecretsManager:
    def __init__(self, key: Optional[str] = None) -> None:
        self._fernet = Fernet(key or get_settings().secrets_key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:  # pragma: no cover - sanity guard
            raise ValueError("Invalid token") from exc


def get_secrets_manager() -> SecretsManager:
    return SecretsManager()
