from loguru import logger

logger.add(
    "logs/roundtable.log",
    rotation="10 MB",
    retention="7 days",
    serialize=True,
)

__all__ = ["logger"]
