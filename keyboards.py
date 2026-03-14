from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, datetime, timedelta
from config import TIMEZONE

def get_note_kb(event_uid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Добавить/Изменить заметку ✍️", callback_data=f"addnote_{event_uid}")
    ]])

def get_schedule_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Сегодня", callback_data="schedule_today"),
         InlineKeyboardButton(text="Завтра", callback_data="schedule_tomorrow")],[InlineKeyboardButton(text="Эта неделя", callback_data="schedule_this_week")],[InlineKeyboardButton(text="⬅️ Пред. неделя", callback_data="schedule_prev_week"),
         InlineKeyboardButton(text="След. неделя ➡️", callback_data="schedule_next_week")]
    ])

def get_day_nav_kb(prev_date: date, next_date: date, monday: date) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="← Вчера", callback_data=f"day_{prev_date.isoformat()}"),
            InlineKeyboardButton(text="Завтра →", callback_data=f"day_{next_date.isoformat()}")
        ],[InlineKeyboardButton(text="📋 Неделя целиком", callback_data=f"week_{monday.isoformat()}")]
    ])

def get_week_nav_kb(monday: date) -> InlineKeyboardMarkup:
    # 1-й ряд кнопок: Пн - Чт
    row1 =[]
    ru_days_1 = ["Пн", "Вт", "Ср", "Чт"]
    for i in range(4):
        d = monday + timedelta(days=i)
        row1.append(InlineKeyboardButton(text=ru_days_1[i], callback_data=f"day_{d.isoformat()}"))
    
    # 2-й ряд кнопок: Пт - Вс
    row2 = []
    ru_days_2 = ["Пт", "Сб", "Вс"]
    for i in range(4, 7):
        d = monday + timedelta(days=i)
        row2.append(InlineKeyboardButton(text=ru_days_2[i-4], callback_data=f"day_{d.isoformat()}"))
        
    # 3-й ряд: Навигация по неделям
    prev_monday = monday - timedelta(days=7)
    next_monday = monday + timedelta(days=7)
    row3 =[
        InlineKeyboardButton(text="← Пред. нед.", callback_data=f"week_{prev_monday.isoformat()}"),
        InlineKeyboardButton(text="След. нед. →", callback_data=f"week_{next_monday.isoformat()}")
    ]
    
    # 4-й ряд: Возврат в сегодня
    today_iso = datetime.now(TIMEZONE).date().isoformat()
    row4 =[InlineKeyboardButton(text="📅 Вернуться в Сегодня", callback_data=f"day_{today_iso}")]
    
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2, row3, row4])