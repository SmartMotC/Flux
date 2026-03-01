from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import and_
import aiosqlite
import random
import string

#БД 1 - пользователи
user_engine = create_engine("sqlite:///./users.db", connect_args={"check_same_thread": False})
UserBase = declarative_base()
UserSessionLocal = sessionmaker(bind=user_engine)


class User(UserBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(15), unique=True)
    password = Column(String)


def create_user_db():
    UserBase.metadata.create_all(bind=user_engine)


def get_db():
    db = UserSessionLocal()
    try:
        yield db
    finally:
        db.close()


#БД для создания комнат
class Rooms:
    async def create(self, player1):
        code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        async with aiosqlite.connect('rooms.db') as db:
            await db.execute(
                "INSERT INTO rooms (code, player1) VALUES (?, ?)",
                (code, player1)
            )
            await db.commit()
        return code

    async def list_open(self):
        async with aiosqlite.connect('rooms.db') as db:
            async with db.execute("SELECT code, player1 FROM rooms WHERE player2 IS NULL") as cursor:
                return await cursor.fetchall()


rooms = Rooms()
create_user_db()
