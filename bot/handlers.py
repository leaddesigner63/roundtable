from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.api_client import api_get, api_post, api_post_stream
from bot.keyboards import main_menu
from bot.states import DialogueStates
from core.config import get_settings

router = Router()
settings = get_settings()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _ensure_user(message)
    await message.answer(
        "Привет! Я организую круглый стол между моделями. Нажмите \"Новое обсуждение\" чтобы начать.",
        reply_markup=main_menu,
    )


async def _ensure_user(message: Message) -> None:
    await api_post(
        "/api/users",
        {
            "telegram_id": message.from_user.id,
            "username": message.from_user.username,
        },
    )


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
    session = await api_post("/api/sessions", payload)
    session_id = session["id"]
    await state.update_data(active_session_id=session_id)
    await state.set_state(DialogueStates.dialogue_running)
    await message.answer("Запускаю обсуждение... это может занять несколько секунд.")
    summary: dict | None = None
    try:
        async for event in api_post_stream(f"/api/sessions/{session_id}/start", {}):
            if event.get("type") == "message":
                author = event.get("author", "Модель")
                content = event.get("content", "")
                if content:
                    await message.answer(f"{author}: {content}")
            elif event.get("type") == "session":
                summary = event
    except Exception:
        await state.clear()
        await message.answer("Не удалось провести обсуждение. Попробуйте позже.")
        return

    await state.clear()
    if summary:
        await message.answer(
            f"Обсуждение завершено. Раундов: {summary.get('current_round', 0)}. Статус: {summary.get('status', 'unknown')}.",
        )
    else:
        info = await api_get(f"/api/sessions/{session_id}")
        await message.answer(
            f"Обсуждение завершено. Раундов: {info['current_round']}. Статус: {info['status']}.",
        )


@router.message(Command("stop"))
@router.message(F.text == "Остановить диалог")
async def stop_dialogue(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    session_id = data.get("active_session_id")
    if not session_id:
        await message.answer("Сейчас нет активного обсуждения.")
        return
    await api_post(f"/api/sessions/{session_id}/stop", {})
    await state.clear()
    await message.answer("Диалог остановлен.")


@router.message(Command("donate"))
@router.message(F.text == "Отблагодарить создателя")
async def donate_handler(message: Message) -> None:
    payment_url = settings.payment_url
    try:
        payload = await api_get("/api/settings/PAYMENT_URL")
        if isinstance(payload, dict) and payload.get("value"):
            payment_url = payload["value"]
    except Exception:  # pragma: no cover - network/runtime failure fallback
        pass
    await message.answer(f"Поддержать проект: {payment_url}")
