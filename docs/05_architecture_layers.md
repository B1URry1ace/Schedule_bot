# 05. Архитектура уровня слоёв и модулей

## 1. Архитектурный стиль

Для `Schedule bot` подходит слоистая архитектура с элементами MVC/MVP-подхода для Telegram-бота:

- **UI** — обработчики сообщений и callback-кнопок, клавиатуры, FSM-состояния;
- **Application** — сценарии использования: показать расписание, сохранить группу, добавить заметку, распознать голос;
- **Domain** — модели расписания, заметок и правил преобразования;
- **Infrastructure** — SQLite, HTTP-запросы к `.ics`, Whisper, локальная LLM, файловая система.

Бот не имеет классического GUI, поэтому UI это Telegram сообщения, inline кнопки и состояния диалога.

## 2. Слои

### 2.1. Presentation
Отвечает за:
- команды `/start`, `/today`, `/tomorrow`, `/week`, `/schedule`;
- inline-кнопки навигации;
- показ текста пользователю;
- FSM-переходы;
- обработку ошибок ввода.

Файлы:
- `handlers.py`
- `keyboards.py`
- `states.py`

### 2.2. Application
Отвечает за сценарии:
- распознать группу и привязать пользователя;
- получить расписание на день/неделю;
- собрать текст ответа;
- добавить или обновить заметку;
- обработать голосовую заметку.

В текущем репозитории этот слой в основном реализован функциями в `handlers.py` и `services.py`.

### 2.3. Domain
Отвечает за:
- внутренние модели данных;
- правила преобразования;
- инварианты;
- стабильный `uid` для событий;
- разделение «событие», «заметка», «привязка группы».

### 2.4. Infrastructure
Отвечает за:
- HTTP-загрузку `.ics`;
- парсинг календаря;
- SQLite-хранилище;
- скачивание голосовых файлов из Telegram;
- Whisper + LM Studio;
- работу с файловой системой и временными файлами.

Файлы:
- `database.py`
- `services.py`
- часть логики в `main.py`

## 3. Модули и ответственность

| Модуль | Ответственность | Основные сущности |
|---|---|---|
| `main.py` | запуск бота, подключение роутера, polling | `Bot`, `Dispatcher` |
| `handlers.py` | команды, callbacks, сценарии, FSM | `Router`, `Message`, `CallbackQuery` |
| `services.py` | работа с расписанием, группами, голосом | `fetch_events`, `get_group_ics_url`, `transcribe_and_format_note` |
| `database.py` | SQLite-персистентность | `save_user`, `get_user_url`, `save_note`, `get_note` |
| `keyboards.py` | inline-кнопки и навигация | `get_schedule_menu_kb`, `get_day_nav_kb`, `get_week_nav_kb` |
| `states.py` | состояния диалога | `SetupState`, `NoteState` |
| `config.py` | конфигурация и справочники | токен, таймзона, LM Studio URL, список групп |

## 4. Правило зависимостей

Рекомендуемое правило:

1. `Presentation` может зависеть от `Application` и `Domain`.
2. `Application` может зависеть от `Domain` и абстракций инфраструктуры.
3. `Domain` не зависит ни от одного другого слоя.
4. `Infrastructure` может зависеть от `Domain`, но не должен содержать UI-логики.
5. `Presentation` не должна напрямую обращаться к таблицам SQLite или HTTP-клиентам.

### Допустимые зависимости
- `handlers.py -> services.py, database.py, keyboards.py, states.py`
- `services.py -> config.py`
- `database.py -> aiosqlite`
- `main.py -> handlers.py`

### Нежелательные зависимости
- прямой SQL в `handlers.py`;
- прямой HTTP-запрос в `handlers.py`;
- логика форматирования расписания внутри `database.py`;
- сохранение токенов в коде вместо окружения.

## 5. Компонентная структура

### Основные компоненты
- **Telegram Bot** — принимает сообщения;
- **Router / Handlers** — роутинг событий;
- **Schedule Service** — загрузка и парсинг расписания;
- **Note Service** — сохранение заметок;
- **Voice Transcription Service** — распознавание голоса;
- **SQLite Repository** — хранение пользователей и заметок;
- **External Schedule Source** — `.ics`-источник;
- **Whisper / LM Studio** — локальная обработка голоса.
