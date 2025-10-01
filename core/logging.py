from loguru import logger

logger.add("logs/roundtable.log", rotation="10 MB", retention="7 days")

__all__ = ["logger"]
