from datetime import datetime, timezone

from sqlalchemy import JSON, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "pk": "pk_%(table_name)s",
            "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
            "ix": "ix_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(column_0_N_name)s",
        },
    )

    type_annotation_map = {
        dict: JSON,
    }


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DeleteMark:
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)


class SubjectBase:
    subject_metadata: Mapped[dict] = mapped_column(JSON, nullable=True)


class ResourceBase:
    resource_metadata: Mapped[dict] = mapped_column(JSON, nullable=True)
    environments_to_check: Mapped[dict] = mapped_column(JSON, nullable=True)
