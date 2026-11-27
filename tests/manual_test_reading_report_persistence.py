
import sys

from app import create_app
from services.reading_report_service import (
    save_reading_report,
    get_reading_report,
    list_reading_reports,
    delete_reading_report
)


def main():
    if len(sys.argv) < 2:
        print(
            "使用方法："
            "python -m tests.manual_test_reading_report_persistence <paper_id>"
        )
        return

    paper_id = int(sys.argv[1])

    app = create_app()

    with app.app_context():
        generated_result = {
            "report": {
                "paper_title": "阅读报告持久化测试",
                "research_background": "这是测试研究背景。",
                "research_problem": "这是测试研究问题。",
                "research_objective": "这是测试研究目标。",
                "research_method": "这是测试研究方法。",
                "experimental_design": "这是测试实验设计。",
                "main_results": "这是测试主要结果。",
                "contributions": "这是测试研究贡献。",
                "limitations": "这是测试研究局限。",
                "future_work": "这是测试未来工作。",
                "overall_summary": "这是一份数据库持久化测试报告。",
                "not_stated": []
            },
            "model": "manual-test-model"
        }

        # 1. 保存报告
        saved = save_reading_report(
            paper_id=paper_id,
            generated_result=generated_result,
            report_type="manual_test"
        )

        report_id = saved["id"]

        print("\n1. 保存成功")
        print("报告 ID：", report_id)

        # 2. 根据报告 ID 查询
        queried = get_reading_report(report_id)

        assert queried["paper_id"] == paper_id
        assert queried["report_data"]["paper_title"] == (
            "阅读报告持久化测试"
        )

        print("\n2. 单条报告查询成功")

        # 3. 查询论文的历史报告
        reports = list_reading_reports(paper_id)

        assert any(
            item["id"] == report_id
            for item in reports
        )

        print("\n3. 历史报告查询成功")
        print("当前报告总数：", len(reports))

        # 4. 删除本次测试记录，避免污染正式数据
        deleted = delete_reading_report(report_id)

        assert deleted is True

        print("\n4. 测试记录删除成功")
        print("\n全部测试通过！")


if __name__ == "__main__":
    main()
