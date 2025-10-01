"""Reply keyboard definitions for the Telegram bot."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Новое обсуждение"),
            KeyboardButton(text="Остановить диалог"),
        ],
        [
            KeyboardButton(text="Отблагодарить создателя"),
        ],
    ],
    resize_keyboard=True,
)
