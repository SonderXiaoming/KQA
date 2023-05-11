from typing import Dict, List, Optional
from sqlmodel import SQLModel
from sqlalchemy.future import select
from sqlalchemy import delete, insert, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from ..setting import FILE_PATH, IMG_PATH
from .model import Question
import os

DB_PATH = os.path.join(FILE_PATH, "data.db")


class SQLA:
    def __init__(self, url: str):
        self.url = f'sqlite+aiosqlite:///{url}'
        self.engine = create_async_engine(self.url, pool_recycle=1500)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def create_all(self):
        os.makedirs(FILE_PATH, exist_ok=True)
        os.makedirs(IMG_PATH, exist_ok=True)
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def query_question(self, group_id: Optional[str] = None, user_id: Optional[str] = None, question: Optional[str] = None) -> List[Question]:
        async with self.async_session() as session:
            async with session.begin():
                sql = select(Question)
                if group_id:
                    sql = sql.filter(Question.group_id == group_id)
                if user_id:
                    sql = sql.filter(Question.user_id == user_id)
                if question:
                    sql = sql.filter(Question)
                result = await session.execute(
                    select(Question)
                )
                data = result.scalars().all()
                return data if data else []

    async def insert_question(self, question: Dict[str, str]) -> int:
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(insert(Question).values(**question))
                return 1

    async def update_question(self, group_id: str, user_id: str, que: str, ans: str) -> int:
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(update(Question).where(Question.group_id == group_id, Question.user_id == user_id, Question.question == que).values(answer=ans))
                return 1

    async def delete_question(self, group_id: str, user_id: str, question: str) -> int:
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(delete(Question).where(Question.group_id == group_id, Question.user_id == user_id, Question.question == question))
                return 1


question_sqla = SQLA(DB_PATH)
