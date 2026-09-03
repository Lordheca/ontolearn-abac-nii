from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from main.models.resources import ServerModel


async def get_server(session: AsyncSession, server_id: int) -> ServerModel | None:
    stmt = select(ServerModel).where(ServerModel.id == server_id)
    stmt = stmt.where(ServerModel.is_deleted.is_(False))
    result = await session.execute(stmt)
    return result.scalars().first()
