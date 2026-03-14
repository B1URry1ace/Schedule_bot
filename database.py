import aiosqlite

async def init_db():
    async with aiosqlite.connect("notes.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, group_name TEXT, ics_url TEXT)")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                user_id INTEGER,
                event_uid TEXT,
                note_text TEXT,
                PRIMARY KEY (user_id, event_uid)
            )
        """)
        await db.commit()
    print("✅ База данных готова")

async def save_user(user_id: int, group_name: str, ics_url: str):
    async with aiosqlite.connect("notes.db") as db:
        await db.execute(
            "INSERT INTO users (user_id, group_name, ics_url) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET group_name = excluded.group_name, ics_url = excluded.ics_url", 
            (user_id, group_name, ics_url)
        )
        await db.commit()

async def get_user_url(user_id: int):
    async with aiosqlite.connect("notes.db") as db:
        async with db.execute("SELECT ics_url FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_note(user_id: int, event_uid: str):
    async with aiosqlite.connect("notes.db") as db:
        async with db.execute("SELECT note_text FROM notes WHERE user_id = ? AND event_uid = ?", (user_id, event_uid)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def save_note(user_id: int, event_uid: str, text: str):
    async with aiosqlite.connect("notes.db") as db:
        await db.execute(
            "INSERT INTO notes (user_id, event_uid, note_text) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, event_uid) DO UPDATE SET note_text = excluded.note_text", 
            (user_id, event_uid, text)
        )
        await db.commit()