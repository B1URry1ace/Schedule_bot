# 06. Интерфейсы


## 1. Основные интерфейсы

### 1.1. `IScheduleProvider`
Источник расписания.

```python
class IScheduleProvider(Protocol):
    async def fetch_events(self, ics_url: str, start_date: date, days: int = 1) -> dict[date, list[ScheduleEvent]]:
        ...
```

Ответственность:
- скачать `.ics`;
- распарсить события;
- привести их к внутреннему формату.

### 1.2. `IGroupResolver`
Преобразует ввод пользователя в календарную ссылку.

```python
class IGroupResolver(Protocol):
    def resolve(self, user_input: str) -> str | None:
        ...
```

Ответственность:
- принять название группы или прямую `.ics`-ссылку;
- вернуть итоговый URL или `None`.

### 1.3. `IStorage`
Постоянное хранилище пользователей и заметок.

```python
class IStorage(Protocol):
    async def save_user(self, user_id: int, group_name: str, ics_url: str) -> None: ...
    async def get_user_url(self, user_id: int) -> str | None: ...
    async def get_note(self, user_id: int, event_uid: str) -> str | None: ...
    async def save_note(self, user_id: int, event_uid: str, text: str) -> None: ...
```

Ответственность:
- сохранять привязку группы;
- хранить заметки;
- читать данные по `user_id`.

### 1.4. `IVoiceTranscriber`
Преобразует голос в текст.

```python
class IVoiceTranscriber(Protocol):
    async def transcribe_and_format(self, file_path: str) -> str:
        ...
```

Ответственность:
- вызвать Whisper;
- очистить и нормализовать текст через локальную LLM;
- вернуть готовую заметку.

### 1.5. `ICache`
Кэш расписания.

```python
class ICache(Protocol):
    def get(self, cache_key: str): ...
    def set(self, cache_key: str, value, ttl_seconds: int) -> None: ...
    def invalidate(self, cache_key: str) -> None: ...
```

Ответственность:
- временно хранить результат запроса к расписанию;
- не допускать повторной загрузки одинаковых данных.

## 2. Типы ошибок уровня приложения

### `InvalidInput`
Неверный ввод пользователя:
- пустая группа;
- неизвестная группа;
- пустая заметка;
- неподдерживаемый тип сообщения.

### `NotFound`
Сущность не найдена:
- у пользователя не настроена группа;
- событие не найдено;
- заметка отсутствует.

### `NetworkError`
Проблема сети:
- не удалось скачать `.ics`;
- таймаут HTTP-запроса;
- Telegram file download failed.

### `RateLimited`
Сервис ограничил число запросов или пользователь слишком часто повторяет действие.

### `ServiceUnavailable`
Внешний сервис недоступен:
- .ics-источник не отвечает;
- LM Studio не запущен;
- локальная модель не поднялась.

### `StorageError`
Ошибка SQLite или файловой системы.

### `TranscriptionError`
Ошибка Whisper или локальной LLM при обработке голосовой заметки.

## 3. Дополнительные контракты

### Формат ошибок для UI
Для пользователя ошибки должны быть короткими и понятными:
- что случилось;
- что можно сделать дальше;
- без внутренних стек-трейсов.

### Контракт для расписания
`fetch_events(...)` должен:
- возвращать словарь по датам;
- сортировать события по времени;
- не терять события при повторном запросе.

### Контракт для заметок
`save_note(...)` должна обновлять существующую заметку, а не создавать дубликаты для одной и той же пары `user_id + event_uid`.

