from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..base import BaseModel, DeleteMark, ResourceBase, TimestampMixin


class LinuxServerModel(BaseModel, ResourceBase, DeleteMark, TimestampMixin):
    __tablename__ = "linux_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ram: Mapped[int] = mapped_column(Integer)
    cpu_cores: Mapped[int] = mapped_column(Integer)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"))
