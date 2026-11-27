from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

if TYPE_CHECKING:
    from models.paper import Paper


class Note(db.Model):

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)

    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 笔记标题
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # 笔记正文
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # 对应的论文页码
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # 是否收藏
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    paper: Mapped["Paper"] = relationship(
        back_populates="notes"
    )