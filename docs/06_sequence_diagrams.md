# 06. Sequence-диаграммы

## 1. Пользователь вводит группу - бот показывает расписание

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant TG as Telegram
    participant H as handlers.py
    participant S as services.py
    participant DB as database.py
    participant ICS as .ics источник

    U->>TG: /start
    TG->>H: command /start
    H->>U: "Напиши номер группы или .ics-ссылку"

    U->>TG: "КТбо3-3"
    TG->>H: текст сообщения
    H->>S: get_group_ics_url("КТбо3-3")
    S-->>H: ics_url
    H->>DB: save_user(user_id, group_name, ics_url)
    DB-->>H: ok
    H->>U: "Группа сохранена" + меню

    U->>TG: /today
    TG->>H: command /today
    H->>DB: get_user_url(user_id)
    DB-->>H: ics_url
    H->>S: fetch_events(ics_url, today, 1)
    S->>ICS: GET .ics
    ICS-->>S: calendar data
    S-->>H: events_by_date
    H->>U: расписание на сегодня
```

## 2. Пользователь добавляет заметку к паре

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant TG as Telegram
    participant H as handlers.py
    participant DB as database.py
    participant V as Whisper / LM Studio

    U->>TG: нажимает "Добавить/Изменить заметку"
    TG->>H: callback addnote_<event_uid>
    H->>H: FSM -> waiting_for_note
    H->>U: "Отправь текст или голосовое сообщение"

    U->>TG: голос / текст
    TG->>H: сообщение
    H->>H: если текст -> взять как есть
    H->>V: если voice -> скачать, распознать, нормализовать
    V-->>H: final_text
    H->>DB: save_note(user_id, event_uid, final_text)
    DB-->>H: ok
    H->>U: "Заметка успешно сохранена"
```

## последовательность

- `handlers.py` управляет диалогом и состоянием.
- `services.py` отвечает за внешние данные и распознавание.
- `database.py` хранит привязку группы и заметки.
- Внешний `.ics`-источник отделён от Telegram-слоя.

