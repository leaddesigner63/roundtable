from __future__ import annotations

import html
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from httpx import HTTPError

from bot.api_client import api_post
from bot.keyboards import main_menu
from bot.states import DialogueStates
from core.config import get_settings

router = Router()
settings = get_settings()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Я организую круглый стол между моделями. Нажмите \"Новое обсуждение\" чтобы начать.",
        reply_markup=main_menu,
    )


async def _ensure_user(message: Message) -> None:
    try:
        await api_post(
            "/api/users",
            {
                "telegram_id": message.from_user.id,
                "username": message.from_user.username,
            },
        )
    except HTTPError:
        # Не критично, продолжим без сохранения пользователя
        return


@router.message(Command("new"))
@router.message(F.text == "Новое обсуждение")
async def new_dialogue(message: Message, state: FSMContext) -> None:
    await _ensure_user(message)
    await state.set_state(DialogueStates.waiting_for_topic)
    await message.answer("Введите тему для обсуждения:")


@router.message(DialogueStates.waiting_for_topic)
async def receive_topic(message: Message, state: FSMContext) -> None:
    topic = message.text.strip()
    if not topic:
        await message.answer("Пожалуйста, отправьте тему текстом.")
        return

    payload = {
        "user_id": message.from_user.id,
        "topic": topic,
    }
    try:
        session = await api_post("/api/sessions", payload)
    except HTTPError:
        await message.answer("Не удалось создать обсуждение. Попробуйте позже.")
        return

    session_id = session["id"]
    await state.update_data(active_session_id=session_id)
    await message.answer("Запускаю обсуждение... это может занять несколько секунд.")
    try:
        started_session = await api_post(f"/api/sessions/{session_id}/start", {})
    except HTTPError:
        await message.answer("Не удалось запустить обсуждение. Попробуйте позже.")
        return
    await state.clear()
    await _send_session_history(message, started_session)


@router.message(Command("stop"))
@router.message(F.text == "Остановить диалог")
async def stop_dialogue(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    session_id = data.get("active_session_id")
    if not session_id:
        await message.answer("Сейчас нет активного обсуждения.")
        return
    try:
        session = await api_post(f"/api/sessions/{session_id}/stop", {"reason": "user"})
    except HTTPError:
        await message.answer("Не удалось остановить обсуждение. Попробуйте позже.")
        return
    await state.clear()
    await message.answer("Диалог остановлен.")
    await _send_session_history(message, session)


@router.message(Command("donate"))
@router.message(F.text == "Отблагодарить создателя")
async def donate_handler(message: Message) -> None:
    await message.answer(f"Поддержать проект: {settings.payment_url}")


async def _send_session_history(message: Message, session: dict[str, Any]) -> None:
    rounds_info = f"Раундов: {session.get('current_round', 0)} из {session.get('max_rounds', 0)}."
    status = session.get("status", "unknown")
    history = session.get("messages", [])
    if not history:
        await message.answer(f"Обсуждение завершено. {rounds_info} Статус: {status}.")
        return

    total_cost = 0.0
    for item in history:
        if item.get("author_type") != "model":
            continue
        total_cost += float(item.get("cost", 0.0))
        author = html.escape(item.get("author_name", "Модель"))
        content = html.escape(item.get("content", ""))
        tokens_in = item.get("tokens_in", 0)
        tokens_out = item.get("tokens_out", 0)
        text = (
            f"<b>{author}</b>\n{content}\n\n"
            f"<i>Входных токенов: {tokens_in}, выходных токенов: {tokens_out}</i>"
        )
        await message.answer(text)

    await message.answer(
        "Обсуждение завершено. "
        f"{rounds_info} Статус: {status}. Суммарная стоимость: {total_cost:.4f}."
    )
