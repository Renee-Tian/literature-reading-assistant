from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ForeignKey,
    Text,
    JSON,
    DateTime,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

if TYPE_CHECKING:
    from models.paper import Paper


class QARecord(db.Model):

    __tablename__ = "qa_records"

    id: Mapped[int] = mapped_column(primary_key=True)

    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 用户提出的问题
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # 大模型生成的回答
    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # 回答引用的原文证据
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    paper: Mapped["Paper"] = relationship(
        back_populates="qa_records"
    )