from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from core.config import settings
from core.db import AsyncSessionMaker
from core.models import User
from worker.tasks import start_session_task

logging.basicConfig(level=logging.INFO)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer("Добро пожаловать в Круглый стол ИИ! Нажмите 'Новое обсуждение'.")


@router.message(Command("new"))
async def cmd_new(message: Message) -> None:
    await message.answer("Опишите тему обсуждения одним сообщением.")


@router.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    await message.answer("Диалог будет остановлен по вашей просьбе.")


@router.message()
async def handle_message(message: Message) -> None:
    text = message.text or ""
    if not text.strip():
        await message.answer("Сообщение пустое, пожалуйста, введите тему.")
        return

    async with AsyncSessionMaker() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            user = User(telegram_id=message.from_user.id, username=message.from_user.username)
            session.add(user)
            await session.commit()

    start_session_task.delay(message.message_id)  # placeholder for worker integration
    await message.answer(
        "Обсуждение будет запущено. Ожидайте уведомления.",
        parse_mode=ParseMode.HTML,
    )


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
