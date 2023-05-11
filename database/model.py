from typing import List, Optional
from sqlmodel import Field, SQLModel

class Question(SQLModel, table=True):
    __table_args__ = {'keep_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True, title='序号')
    group_id: Optional[str] = Field(default="all", title="群号")
    user_id: Optional[str] = Field(default="all", title='用户QQ')
    question: str = Field(title="问题")
    answer: str = Field(title='答案')
