#(Бизнес-логика, API, нейросети) Здесь выполняется "тяжёлая" работа: загружаются нейросети, скачивается и парсится ics, распознается аудио.

import asyncio
import aiohttp
import hashlib
import re
from datetime import datetime, date, timedelta
from icalendar import Calendar
from faster_whisper import WhisperModel
import openai

from config import TIMEZONE, GROUPS_LOWER, LM_STUDIO_URL, LM_STUDIO_API_KEY, WHISPER_MODEL_NAME

# Инициализируем модели нейросетей при запуске файла
print("Загрузка модели Whisper...")
whisper_model = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
print("Whisper готов!")

lm_client = openai.AsyncOpenAI(base_url=LM_STUDIO_URL, api_key=LM_STUDIO_API_KEY)

def get_group_ics_url(user_input: str):
    user_input = user_input.strip().lower()
    if "schedule.rdcenter.ru" in user_input and ".ics" in user_input:
        return user_input 
    person_id = GROUPS_LOWER.get(user_input)
    if person_id:
        return f"https://schedule.rdcenter.ru/api/Schedule/ics?attendeePersonId={person_id}"
    return None

def get_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())

async def fetch_events(ics_url: str, start_date: date, days: int = 1):
    end_date = start_date + timedelta(days=days - 1)
    async with aiohttp.ClientSession() as session:
        async with session.get(ics_url) as response:
            ics_data = await response.read()

    cal = Calendar.from_ical(ics_data)
    events_by_date = {}

    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart = component.get('dtstart').dt
            if isinstance(dtstart, datetime):
                dtstart = dtstart.astimezone(TIMEZONE)
                event_date = dtstart.date()
                start_str = dtstart.strftime("%H:%M")
            else:
                event_date = dtstart
                start_str = "Весь день"

            if start_date <= event_date <= end_date:
                dtend = component.get('dtend').dt
                end_str = dtend.astimezone(TIMEZONE).strftime("%H:%M") if isinstance(dtend, datetime) else ""

                summary = str(component.get('summary'))
                desc = str(component.get('description') or "").replace('\\n', '\n').replace('\\,', ',')

                aud_match = re.search(r"Аудитория:\s*([^\n]+)", desc)
                classroom = aud_match.group(1).strip() if aud_match else None
                teacher_match = re.search(r"Преподаватели:\s*([^\n]+)", desc)
                teacher = teacher_match.group(1).strip() if teacher_match else None

                stable_uid = hashlib.md5(f"{event_date.isoformat()}_{start_str}_{summary}".encode()).hexdigest()

                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append({
                    "uid": stable_uid,
                    "summary": summary,
                    "start": start_str,
                    "end": end_str,
                    "classroom": classroom,
                    "teacher": teacher
                })

    for d in events_by_date:
        events_by_date[d].sort(key=lambda x: x['start'])
    return events_by_date

async def transcribe_and_format_note(file_path: str) -> str:
    """Распознает голос через Whisper и оформляет через LM Studio."""
    loop = asyncio.get_running_loop()
    # Запускаем Whisper в отдельном потоке
    raw_text = await loop.run_in_executor(
        None, 
        lambda: " ".join([segment.text for segment in whisper_model.transcribe(file_path, beam_size=5, language="ru")[0]])
    )

    # Улучшаем через локальную LLM
    response = await lm_client.chat.completions.create(
        model="local-model",
        messages=[
            {"role": "system", "content": "Исправь ошибки распознавания, расставь знаки препинания и верни только чистый текст заметки. Ничего не добавляй от себя."},
            {"role": "user", "content": raw_text}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()