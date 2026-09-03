from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import BaseModel, DeleteMark, ResourceBase, TimestampMixin


class ServerModel(BaseModel, ResourceBase, DeleteMark, TimestampMixin):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location: Mapped[str] = mapped_column(String(100), unique=True)
