from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import BaseModel, DeleteMark, SubjectBase, TimestampMixin


class UserModel(BaseModel, SubjectBase, DeleteMark, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(255))
