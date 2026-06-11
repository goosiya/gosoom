import uuid as _uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProCategory(Base):
    __tablename__ = "pro_categories"

    user_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    category_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
