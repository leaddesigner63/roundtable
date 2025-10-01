from aiogram.fsm.state import State, StatesGroup


class DialogueStates(StatesGroup):
    waiting_for_topic = State()
