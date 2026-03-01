# tasks.py — ПУСТАЯ БД заданий
import aiosqlite

async def init_tasks_db():
    """🆕 Создать ПУСТУЮ БД заданий"""
    async with aiosqlite.connect('tasks.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                test_code TEXT NOT NULL,
                expected_output TEXT NOT NULL
            )
        ''')
        await db.commit()
        print("✅ tasks.db создана (ПУСТАЯ)")
