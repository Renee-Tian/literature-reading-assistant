from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

if TYPE_CHECKING:
    from models.note import Note
    from models.paper_chunk import PaperChunk
    from models.qa_record import QARecord
    from models.reading_report import ReadingReport


class Paper(db.Model):
    """
    学术论文数据模型。
    对应 MySQL 中的 papers 数据表。
    """

    __tablename__ = "papers"

    # 论文唯一编号
    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # 论文标题
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    # 作者
    authors: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    # 论文摘要
    abstract: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # 发表年份
    publication_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # 用户上传时的原始文件名
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # 系统保存时的文件名
    stored_filename: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    # 文件实际存储路径
    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False
    )

    # 文献处理状态
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="uploaded",
        index=True
    )

    # 处理失败时的错误信息
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    # 修改时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now())

        # 与论文文本块的一对多关系
    paper_chunks: Mapped[list["PaperChunk"]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan"
    )

    # 与阅读报告的一对多关系
    reading_reports: Mapped[list["ReadingReport"]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan"
    )

    # 与历史问答的一对多关系
    qa_records: Mapped[list["QARecord"]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan"
    )

    # 与阅读笔记的一对多关系
    notes: Mapped[list["Note"]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan"
    )
    

    def __repr__(self):
        return f"<Paper {self.id}: {self.title}>"