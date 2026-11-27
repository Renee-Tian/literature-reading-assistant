
import json
# 延迟导入，避免与模型模块产生不必要的循环依赖。
from models import ReadingReport as ReadingReportModel

from database.db import db
from models import Paper
from repositories.reading_report_repository import (
    ReadingReportRepository
)


class ReadingReportServiceError(Exception):
    """阅读报告持久化业务异常。"""


def serialize_reading_report(report):
    """将阅读报告模型对象转换为可返回的字典。"""

    return {
        "id": report.id,
        "paper_id": report.paper_id,
        "report_type": report.report_type,
        "report_data": report.report_data,
        "model_name": report.model_name,
        "created_at": (
            report.created_at.isoformat()
            if report.created_at
            else None
        )
    }


def validate_generated_result(generated_result):
    """检查大模型生成结果是否符合保存要求。"""

    if not isinstance(generated_result, dict):
        raise ReadingReportServiceError(
            "生成结果必须是字典类型。"
        )

    report = generated_result.get("report")

    if not isinstance(report, dict) or not report:
        raise ReadingReportServiceError(
            "生成结果中缺少有效的 report 数据。"
        )

    try:
        json.dumps(report, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ReadingReportServiceError(
            "报告内容无法转换为 JSON。"
        ) from exc

    return report


def save_reading_report(
    paper_id,
    generated_result,
    report_type="literature_reading"
):
    """保存大模型生成的阅读报告。"""

    if not isinstance(paper_id, int) or isinstance(paper_id, bool):
        raise ReadingReportServiceError(
            "paper_id 必须是整数。"
        )

    if not isinstance(report_type, str) or not report_type.strip():
        raise ReadingReportServiceError(
            "report_type 不能为空。"
        )

    report_data = validate_generated_result(
        generated_result
    )

    paper = db.session.get(Paper, paper_id)

    if paper is None:
        raise ReadingReportServiceError(
            f"论文不存在，paper_id={paper_id}。"
        )

    model_name = generated_result.get("model") or "unknown"

    if not isinstance(model_name, str):
        raise ReadingReportServiceError(
            "模型名称必须是字符串。"
        )

    try:
        report = ReadingReportModel(
            paper_id=paper_id,
            report_type=report_type.strip(),
            report_data=report_data,
            model_name=model_name
        )

        ReadingReportRepository.add(report)

        db.session.commit()

        return serialize_reading_report(report)

    except Exception as exc:
        db.session.rollback()

        if isinstance(exc, ReadingReportServiceError):
            raise

        raise ReadingReportServiceError(
            f"阅读报告保存失败：{str(exc)}"
        ) from exc


def get_reading_report(report_id):
    """根据报告 ID 获取阅读报告。"""

    report = ReadingReportRepository.get_by_id(report_id)

    if report is None:
        raise ReadingReportServiceError(
            f"阅读报告不存在，report_id={report_id}。"
        )

    return serialize_reading_report(report)


def list_reading_reports(paper_id):
    """获取某篇论文的全部阅读报告。"""

    paper = db.session.get(Paper, paper_id)

    if paper is None:
        raise ReadingReportServiceError(
            f"论文不存在，paper_id={paper_id}。"
        )

    reports = ReadingReportRepository.list_by_paper_id(
        paper_id
    )

    return [
        serialize_reading_report(report)
        for report in reports
    ]


def get_latest_reading_report(paper_id):
    """获取某篇论文最新的阅读报告。"""

    paper = db.session.get(Paper, paper_id)

    if paper is None:
        raise ReadingReportServiceError(
            f"论文不存在，paper_id={paper_id}。"
        )

    report = ReadingReportRepository.get_latest_by_paper_id(
        paper_id
    )

    if report is None:
        return None

    return serialize_reading_report(report)


def delete_reading_report(report_id):
    """删除一份阅读报告。"""

    report = ReadingReportRepository.get_by_id(report_id)

    if report is None:
        raise ReadingReportServiceError(
            f"阅读报告不存在，report_id={report_id}。"
        )

    try:
        ReadingReportRepository.delete(report)
        db.session.commit()
        return True

    except Exception as exc:
        db.session.rollback()

        raise ReadingReportServiceError(
            f"阅读报告删除失败：{str(exc)}"
        ) from exc


