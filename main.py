from fastapi import FastAPI, Depends, HTTPException, WebSocket
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database import get_db, User, rooms
import uvicorn
import aiosqlite
from tasks import init_tasks_db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup():
    print("🚀 Создаём БД...")
    await init_tasks_db()  # ← СОЗДАЁТ таблицу!
    print("✅ БД готова!")

# =================== ТВОИ ЮЗЕРЫ (добавлен token!) ===================
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse('index.html')


@app.get("/users/all_users")
async def get_all_users(db1: Session = Depends(get_db)):
    users = db1.query(User).all()
    return users


@app.post("/users/registration", tags=["Registration"])
async def registration(name: str, password: str, db1: Session = Depends(get_db)):
    existing = db1.query(User).filter(User.name == name).first()
    if existing:
        raise HTTPException(400, "Пользователь уже существует!")

    user = User(name=name, password=password)
    db1.add(user)
    db1.commit()
    db1.refresh(user)
    return {"id": user.id, "name": user.name}


@app.post("/users/login", tags=["Registration"])
async def login_user(name: str, password: str, db1: Session = Depends(get_db)):
    user = db1.query(User).filter(
        and_(User.name == name, User.password == password)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден!")

    token = str(user.id)

    return {
        "message": "✅ Вход успешен!",
        "user_id": user.id,
        "name": user.name,
        "token": token
    }


# =================== КОМНАТЫ (автоматически твой ник!) ===================
@app.on_event("startup")
async def startup():
    async with aiosqlite.connect('rooms.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS rooms (
            code TEXT PRIMARY KEY, 
            player1 TEXT, 
            player2 TEXT
        )''')
        await db.commit()


@app.get("/rooms")
async def get_rooms():
    return [{"code": r[0], "player1": r[1]} for r in await rooms.list_open()]


@app.post("/rooms")
async def create_room_endpoint(player1: str):
    code = await rooms.create(player1)
    return {"code": code}


@app.websocket("/ws/{code}")
async def code_duel(websocket: WebSocket, code: str):
    await websocket.accept()

    if not hasattr(code_duel, "players"):
        code_duel.players = {}
    if code not in code_duel.players:
        code_duel.players[code] = []

    players = code_duel.players[code]
    players.append(websocket)

    if len(players) == 2:
        for ws in players:
            await ws.send_text("{'type': 'battle_ready', 'message': '⚔️ Код соперника онлайн!'}")

    try:
        while True:
            data = await websocket.receive_json()
            for ws in players:
                if ws != websocket:
                    await ws.send_json({
                        "type": "rival_code",
                        "code": data["code"],
                        "player": data.get("player", "Соперник")
                    })
    except:
        pass


# 🆕 Админ endpoint
@app.post("/admin/tasks/add", tags=["Admin"])
async def add_task(
        title: str,
        description: str,
        test_code: str,
        expected_output: str
):
    """🔥 Админ: Добавить новое задание"""

    async with aiosqlite.connect('tasks.db') as db:
        # Проверка дубликатов
        async with db.execute("SELECT id FROM tasks WHERE title=?", (title,)) as c:
            if await c.fetchone():
                raise HTTPException(400, "Задание уже существует!")

        # Добавляем задание
        await db.execute('''
            INSERT INTO tasks (title, description, test_code, expected_output) 
            VALUES (?, ?, ?, ?)
        ''', (title, description, test_code, expected_output))

        await db.commit()
        return {"status": "✅ Задание добавлено!", "title": title}


# 🆕 GET — все задания
@app.get("/tasks", tags=["Admin"])
async def get_tasks():
    """📋 Получить список заданий"""
    async with aiosqlite.connect('tasks.db') as db:
        # Выбираем ID, название, описание (для списка)
        async with db.execute("""
            SELECT id, title, description 
            FROM tasks 
            ORDER BY id ASC
        """) as cursor:
            rows = await cursor.fetchall()

    # Превращаем в JSON
    tasks = []
    for row in rows:
        tasks.append({
            "id": row[0],
            "title": row[1],
            "description": row[2]
        })

    return tasks


# Добавь В КОНЕЦ main.py (10 строк!):

@app.post("/tasks/{task_id}/check")
async def check_code(task_id: int, code: str):
    """✅ ПРОВЕРКА КОДА ИГРОКА"""
    async with aiosqlite.connect('tasks.db') as db:
        async with db.execute("SELECT test_code, expected_output FROM tasks WHERE id=?", (task_id,)) as c:
            task = await c.fetchone()
            if not task:
                raise HTTPException(404, "Задание не найдено!")

    test_code, expected = task
    import sys, io
    old_stdout = sys.stdout
    sys.stdout = out = io.StringIO()

    try:
        exec(code + "\n" + test_code)  # Код игрока + тест
        result = out.getvalue().strip()
        sys.stdout = old_stdout
        return {
            "correct": result == expected.strip(),
            "output": result,
            "expected": expected
        }
    except Exception as e:
        sys.stdout = old_stdout
        return {"correct": False, "error": str(e)}

# Админ DELETE задание
@app.delete("/admin/tasks/{task_id}")
async def delete_task(task_id: int):
    async with aiosqlite.connect('tasks.db') as db:
        await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        await db.commit()
    return {"status": "✅ Задание удалено!"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
