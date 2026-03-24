# 04. Модель предметной области + DTO + маппинг


## 1. Domain-модели

### 1.1. `GroupBinding`
Привязка пользователя Telegram к группе расписания.

Поля:
- `user_id: int` — Telegram ID пользователя;
- `group_name: str` — название группы, введённое пользователем;
- `ics_url: str` — итоговый URL календаря;
- `updated_at: datetime | None` — время последнего изменения привязки.

Назначение:
- хранить связь «пользователь → расписание»;
- использовать при запросах `/today`, `/tomorrow`, `/week`, навигации по кнопкам.

### 1.2. `ScheduleEvent`
Событие расписания, уже приведённое к внутреннему формату.

Поля:
- `uid: str` — стабильный идентификатор события;
- `summary: str` — название пары;
- `start: str` — время начала в формате `HH:MM` или `Весь день`;
- `end: str` — время окончания в формате `HH:MM`;
- `classroom: str | None` — аудитория;
- `teacher: str | None` — преподаватель;
- `is_online: bool` — признак онлайн-формата;
- `event_date: date` — дата занятия.

### 1.3. `DaySchedule`
Расписание на один день.

Поля:
- `date: date`;
- `events: list[ScheduleEvent]`.

### 1.4. `WeekSchedule`
Расписание на неделю.

Поля:
- `monday: date`;
- `days: dict[date, list[ScheduleEvent]]`.

### 1.5. `Note`
Личная заметка пользователя к конкретному событию.

Поля:
- `user_id: int`;
- `event_uid: str`;
- `note_text: str`;
- `updated_at: datetime | None`.

### 1.6. `AppSettings`
Глобальные параметры приложения.

Поля:
- `timezone: str`;
- `default_week_days: int = 7`;
- `voice_language: str = "ru"`;
- `schedule_cache_ttl_minutes: int`;
- `network_timeout_seconds: int`.

### 1.7. `CacheEntry`
Запись кэша для расписания.

Поля:
- `cache_key: str`;
- `payload: Any`;
- `expires_at: datetime`.

## 2. DTO (внешние форматы данных)

### 2.1. `IcsCalendarDTO`
Сырые данные календаря, получаемые по HTTP.

Поля:
- `source_url: str`;
- `raw_bytes: bytes`;
- `content_type: str | None`;
- `fetched_at: datetime`.

### 2.2. `IcsEventDTO`
Нормализованное представление `VEVENT` из `.ics`.

Поля:
- `dtstart: datetime | date`;
- `dtend: datetime | date | None`;
- `summary: str | None`;
- `description: str | None`;
- `location: str | None`;
- `uid: str | None`.

### 2.3. `UsersRowDTO`
Строка таблицы `users` из SQLite.

Поля:
- `user_id: int`;
- `group_name: str`;
- `ics_url: str`.

### 2.4. `NotesRowDTO`
Строка таблицы `notes` из SQLite.

Поля:
- `user_id: int`;
- `event_uid: str`;
- `note_text: str`.

### 2.5. `VoiceNoteFileDTO`
Данные о временном голосовом файле Telegram.

Поля:
- `file_id: str`;
- `local_path: str`;
- `mime_type: str | None`;
- `duration_seconds: int | None`.

## 3. Инварианты и ограничения данных

1. `group_name` не пустой.
2. `ics_url` либо:
   - прямой URL на `.ics`, либо
   - ссылка на `schedule.rdcenter.ru` с `attendeePersonId`.
3. Времена событий приводятся к таймзоне `Europe/Moscow`.
4. Для события формируется стабильный `uid`, чтобы заметка не «терялась» при повторном получении расписания.
5. `note_text` после очистки не пустой.
6. Длина заметки должна укладываться в лимит сообщения Telegram; безопасный практический предел — до ~4000 символов.
7. `days` для недельного просмотра всегда `7`.
8. `event_date` должен попадать в запрашиваемый диапазон, иначе событие не включается в выдачу.
9. Для одного `user_id` и `event_uid` существует максимум одна заметка.
10. Значения `teacher` и `classroom` необязательны: они могут отсутствовать в исходном `.ics`.

## 4. Маппинг DTO -> Domain

| DTO / источник | Domain | Преобразование | Примечание |
|---|---|---|---|
| `IcsCalendarDTO` | `WeekSchedule` / `DaySchedule` | парсинг `Calendar.from_ical(...)` | календарь разбирается на события |
| `IcsEventDTO.dtstart` | `ScheduleEvent.event_date`, `ScheduleEvent.start` | если `datetime` — перевод в `Europe/Moscow`; если `date` — `Весь день` | логика совпадает с текущей реализацией |
| `IcsEventDTO.dtend` | `ScheduleEvent.end` | если `datetime` — формат `HH:MM` | для событий на весь день может быть пустым |
| `IcsEventDTO.summary` | `ScheduleEvent.summary` | `str(...)` с защитой от `None` | название пары обязательно |
| `IcsEventDTO.description` | `ScheduleEvent.classroom`, `ScheduleEvent.teacher` | извлечение по шаблонам `Аудитория:` и `Преподаватели:` | regex по описанию |
| `UsersRowDTO` | `GroupBinding` | прямое отображение полей | используется для восстановления привязки |
| `NotesRowDTO` | `Note` | прямое отображение полей | заметка хранится по паре `(user_id, event_uid)` |
| `VoiceNoteFileDTO` | `Note` (через `note_text`) | голос -> скачивание -> Whisper -> локальная LLM -> текст | временный путь удаляется после обработки |

## 5. Правила преобразований

### 5.1. Формирование UID события
Стабильный идентификатор строится из:
- даты события;
- времени начала;
- названия занятия.

Это позволяет сохранять заметки даже если календарь приходит повторно.

### 5.2. Разбор описания события
Из `description` извлекаются:
- аудитория;
- преподаватель.

Если шаблон не найден, поле остаётся `None`.

### 5.3. Обработка дат и времени
Если `dtstart`/`dtend` представлены как `datetime`, они переводятся в `Europe/Moscow`.  
Если `dtstart` представлен как `date`, событие считается «на весь день».

### 5.4. Обработка голосовых заметок
Голосовое сообщение проходит цепочку:
1. скачивание файла;
2. распознавание через Whisper;
3. постобработка текста локальной LLM;
4. сохранение заметки в БД.
