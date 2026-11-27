from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ForeignKey,
    String,
    JSON,
    DateTime,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

if TYPE_CHECKING:
    from models.paper import Paper


class ReadingReport(db.Model):

    __tablename__ = "reading_reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 报告类型
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="comprehensive"
    )

    # 结构化阅读报告
    report_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False
    )

    # 生成报告所使用的模型名称
    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    paper: Mapped["Paper"] = relationship(
        back_populates="reading_reports"
    )