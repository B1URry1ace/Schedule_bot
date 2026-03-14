import os
from datetime import datetime, date, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import services as srv
import keyboards as kb
from states import SetupState, NoteState
from config import TIMEZONE

router = Router()

# --- ФОРМАТИРОВАНИЕ СООБЩЕНИЙ ---
async def send_day_schedule(message: Message, ics_url: str, target_date: date, user_id: int):
    events_dict = await srv.fetch_events(ics_url, target_date, 1)
    events = events_dict.get(target_date,[])

    ru_days =["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    date_str = f"{target_date.strftime('%d.%m.%Y')} — {ru_days[target_date.weekday()]}"

    if not events:
        await message.answer(f"📅 <b>{date_str}</b>\n\nНа этот день занятий нет 🎉", parse_mode="HTML")
        return

    await message.answer(f"📅 <b>Расписание на {date_str}</b>\n", parse_mode="HTML")

    for event in events:
        format_info = f"🏢 <b>Ауд:</b> {event['classroom']}" if event['classroom'] else "🌐 <b>Онлайн</b>"
        teacher_info = f"\n👨‍🏫 <b>Преподаватель:</b> {event['teacher']}" if event['teacher'] else ""
        note = await db.get_note(user_id, event['uid'])
        note_text = f"\n\n📝 <b>Заметка:</b> <i>{note}</i>" if note else ""
        
        text = (f"🕒 <b>{event['start']} — {event['end']}</b>\n"
                f"🎓 <b>{event['summary']}</b>\n"
                f"{format_info}{teacher_info}{note_text}")
        
        await message.answer(text, reply_markup=kb.get_note_kb(event['uid']), parse_mode="HTML")

    prev_date = target_date - timedelta(days=1)
    next_date = target_date + timedelta(days=1)
    monday = srv.get_monday(target_date)
    await message.answer("Навигация:", reply_markup=kb.get_day_nav_kb(prev_date, next_date, monday))

async def send_week_schedule(message: Message, ics_url: str, monday: date):
    events_dict = await srv.fetch_events(ics_url, monday, 7)
    ru_short =["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    week_lines =[f"📅 <b>Неделя с {monday.strftime('%d.%m.%Y')}</b>\n"]

    for i in range(7):
        current_date = monday + timedelta(days=i)
        day_name = ru_short[current_date.weekday()]
        events = events_dict.get(current_date,[])
        header = f"\n<b>{day_name} {current_date.strftime('%d.%m')}</b> {'— выходной 🌴' if not events else ''}"
        week_lines.append(header)
        if events:
            for event in events:
                classroom = f" ({event['classroom']})" if event['classroom'] else " (онлайн)"
                week_lines.append(f"   🕒 {event['start']}—{event['end']} — {event['summary']}{classroom}")

    full_text = "\n".join(week_lines)
    
    # Новая клавиатура с выбором конкретного дня
    markup = kb.get_week_nav_kb(monday)

    if len(full_text) > 3800:
        await message.answer(full_text[:3800] + "\n...", parse_mode="HTML")
        await message.answer("Выберите день для заметок:", reply_markup=markup, parse_mode="HTML")
    else:
        await message.answer(full_text, reply_markup=markup, parse_mode="HTML")

# --- КОМАНДЫ ---
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "Привет! Я бот расписания. 🎓\nНапиши номер своей группы (например: `КТбо3-3`) "
        "или отправь прямую ссылку на .ics файл."
    )
    await state.set_state(SetupState.waiting_for_group)

@router.message(SetupState.waiting_for_group)
async def process_group_input(message: Message, state: FSMContext):
    user_input = message.text.strip()
    ics_url = srv.get_group_ics_url(user_input)
    if ics_url:
        await db.save_user(message.from_user.id, user_input, ics_url)
        await message.answer("✅ Группа сохранена!\n\nКоманды:\n/schedule — главное меню\n/today — сегодня\n/week — неделя")
        await state.clear()
    else:
        await message.answer("❌ Группа не найдена. Попробуй ещё раз или пришли прямую .ics-ссылку.")

@router.message(Command("schedule"))
async def cmd_schedule(message: Message):
    await message.answer("📚 <b>Выбери период:</b>", reply_markup=kb.get_schedule_menu_kb(), parse_mode="HTML")

@router.message(Command("today"))
async def cmd_today(message: Message):
    ics_url = await db.get_user_url(message.from_user.id)
    if not ics_url:
        return await message.answer("Сначала настрой группу /start")
    await send_day_schedule(message, ics_url, datetime.now(TIMEZONE).date(), message.from_user.id)

@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message):
    ics_url = await db.get_user_url(message.from_user.id)
    if not ics_url:
        return await message.answer("Сначала настрой группу /start")
    tomorrow = datetime.now(TIMEZONE).date() + timedelta(days=1)
    await send_day_schedule(message, ics_url, tomorrow, message.from_user.id)

@router.message(Command("week"))
async def cmd_week(message: Message):
    ics_url = await db.get_user_url(message.from_user.id)
    if not ics_url:
        return await message.answer("Сначала настрой группу /start")
    await send_week_schedule(message, ics_url, srv.get_monday(datetime.now(TIMEZONE).date()))

# --- CALLBACKS (НАВИГАЦИЯ) ---
@router.callback_query(F.data.startswith("day_"))
async def callback_day_nav(callback: CallbackQuery):
    ics_url = await db.get_user_url(callback.from_user.id)
    if not ics_url:
        return await callback.answer("Группа не настроена")
    
    # Берем дату из callback и открываем конкретный день
    target_date = date.fromisoformat(callback.data.split("_")[1])
    
    # Удаляем старое сообщение с меню, чтобы не засорять чат
    try:
        await callback.message.delete()
    except:
        pass
        
    await send_day_schedule(callback.message, ics_url, target_date, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data.startswith("week_"))
async def callback_week_nav(callback: CallbackQuery):
    ics_url = await db.get_user_url(callback.from_user.id)
    if not ics_url:
        return await callback.answer("Группа не настроена")
    monday = date.fromisoformat(callback.data.split("_")[1])
    
    try:
        await callback.message.delete()
    except:
        pass
        
    await send_week_schedule(callback.message, ics_url, monday)
    await callback.answer()

@router.callback_query(F.data.startswith("schedule_"))
async def callback_main_menu(callback: CallbackQuery):
    ics_url = await db.get_user_url(callback.from_user.id)
    if not ics_url:
        return await callback.answer("Сначала настрой группу через /start", show_alert=True)

    action = callback.data.split("_", 1)[1]
    today = datetime.now(TIMEZONE).date()

    try:
        await callback.message.delete()
    except:
        pass

    if action == "today":
        await send_day_schedule(callback.message, ics_url, today, callback.from_user.id)
    elif action == "tomorrow":
        await send_day_schedule(callback.message, ics_url, today + timedelta(days=1), callback.from_user.id)
    elif action == "this_week":
        await send_week_schedule(callback.message, ics_url, srv.get_monday(today))
    elif action == "next_week":
        await send_week_schedule(callback.message, ics_url, srv.get_monday(today) + timedelta(days=7))
    elif action == "prev_week": # Добавили прошлую неделю
        await send_week_schedule(callback.message, ics_url, srv.get_monday(today) - timedelta(days=7))
        
    await callback.answer()

# --- CALLBACKS (ЗАМЕТКИ) ---
@router.callback_query(F.data.startswith("addnote_"))
async def process_add_note_btn(callback: CallbackQuery, state: FSMContext):
    event_uid = callback.data.split("_")[1]
    await state.update_data(event_uid=event_uid, user_id=callback.from_user.id)
    await state.set_state(NoteState.waiting_for_note)
    await callback.message.answer("📝 Отправь текст заметки или **голосовое сообщение** 🎙️", parse_mode="HTML")
    await callback.answer("Ожидаю заметку...")

@router.message(NoteState.waiting_for_note, F.content_type.in_({'text', 'voice'}))
async def process_note_input(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    event_uid = data.get("event_uid")
    user_id = data.get("user_id")

    if not event_uid or not user_id:
        await message.answer("❌ Ошибка состояния. Попробуй заново.")
        return await state.clear()

    if message.text:
        final_text = message.text.strip()
    elif message.voice:
        processing_msg = await message.answer("⏳ Распознаю голос...")
        file_path = f"voice_{message.voice.file_id}.ogg"
        
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, file_path)

        try:
            await processing_msg.edit_text("🧠 Обрабатываю текст через LM Studio...")
            final_text = await srv.transcribe_and_format_note(file_path)
            await processing_msg.delete()
            await message.answer(f"✅ Распознано и сохранено:\n<i>{final_text}</i>", parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка: {e}")
            return await processing_msg.edit_text("❌ Ошибка при распознавании.")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        return await message.answer("❌ Отправь текст или голосовое.")

    await db.save_note(user_id, event_uid, final_text)
    await state.clear()
    await message.answer("✅ Заметка успешно сохранена! Вызови расписание, чтобы проверить.")