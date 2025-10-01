from __future__ import annotations

from aiogram import F, Router, types
from aiogram.filters import Command
from sqlalchemy import select

from core.config import settings
from core.database import SessionLocal
from core.models import Personality, Provider, SessionStatus
from core.services import create_session, get_or_create_user, update_session_status
from worker.tasks import enqueue_session_run

router = Router()


async def _build_menu() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Новое обсуждение")],
            [types.KeyboardButton(text="Остановить диалог")],
            [types.KeyboardButton(text="Отблагодарить создателя")],
        ],
        resize_keyboard=True,
    )


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    keyboard = await _build_menu()
    await message.answer(
        "Привет! Я организую обсуждения между моделями. Нажмите 'Новое обсуждение' чтобы начать.",
        reply_markup=keyboard,
    )


@router.message(Command("donate"))
async def cmd_donate(message: types.Message) -> None:
    await message.answer(f"Поддержать проект: {settings.payment_url}")


@router.message(F.text == "Отблагодарить создателя")
async def donate_button(message: types.Message) -> None:
    await cmd_donate(message)


@router.message(F.text == "Новое обсуждение")
async def prompt_new_topic(message: types.Message) -> None:
    await message.answer("Введите тему обсуждения командой /new <тема>.")


@router.message(Command("new"))
async def cmd_new(message: types.Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) == 1:
        await message.answer("Укажите тему после команды /new")
        return
    topic = args[1]

    async with SessionLocal() as db:
        user = await get_or_create_user(
            db,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )
        providers = (
            await db.execute(select(Provider).where(Provider.enabled.is_(True)).order_by(Provider.order_index))
        ).scalars().all()
        personalities = (await db.execute(select(Personality).order_by(Personality.id))).scalars().all()
        if not providers or not personalities:
            await message.answer("Сначала настройте провайдеров и персоналии в админке.")
            return
        pairs = []
        for index, provider in enumerate(providers):
            personality = personalities[index % len(personalities)]
            pairs.append((provider, personality))
        session_obj = await create_session(db, user=user, topic=topic, participants=pairs, max_rounds=settings.max_rounds)
        session_obj.status = SessionStatus.CREATED
        await db.commit()
    enqueue_session_run(session_obj.id)
    await message.answer(f"Сессия #{session_obj.id} создана и запущена!")


@router.message(Command("stop"))
async def cmd_stop(message: types.Message) -> None:
    async with SessionLocal() as db:
        user = await get_or_create_user(
            db,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )
        result = await db.execute(
            select(Session)
            .where(Session.user_id == user.telegram_id, Session.status == SessionStatus.RUNNING)
            .order_by(Session.id.desc())
        )
        session_obj = result.scalars().first()
        if not session_obj:
            await message.answer("Нет активных обсуждений для остановки.")
            return
        await update_session_status(db, session_obj, SessionStatus.STOPPED)
        await db.commit()
    await message.answer(f"Сессия #{session_obj.id} остановлена.")


@router.message(F.text == "Остановить диалог")
async def stop_button(message: types.Message) -> None:
    await cmd_stop(message)
