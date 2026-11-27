from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
    UniqueConstraint,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

if TYPE_CHECKING:
    from models.paper import Paper


class PaperChunk(db.Model):

    __tablename__ = "paper_chunks"

    __table_args__ = (
        UniqueConstraint(
            "paper_id",
            "chunk_index",
            name="uq_paper_chunk_position"
        ),
        {"mysql_engine": "InnoDB"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # 所属论文 ID：外键
    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 文本块在论文中的顺序
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    # 文本块内容
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # 所在 PDF 页码
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # 所属章节
    section_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # Token 数量（可选）
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    # 与 Paper 建立关联
    paper: Mapped["Paper"] = relationship(
        back_populates="paper_chunks"
    )