#(Машина состояний)
#Здесь лежат классы FSM (ожидание ввода)

from aiogram.fsm.state import StatesGroup, State

class SetupState(StatesGroup):
    waiting_for_group = State()

class NoteState(StatesGroup):
    waiting_for_note = State()