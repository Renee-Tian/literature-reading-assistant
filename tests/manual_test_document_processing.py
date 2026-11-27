
import sys
from pprint import pprint

from app import create_app
from services.document_processing_service import (
    DocumentProcessingService,
    DocumentProcessingError
)


def main():
    if len(sys.argv) < 2:
        print(
            "使用方法：python -m tests.manual_test_document_processing <paper_id>"
        )
        return

    paper_id = int(sys.argv[1])

    app = create_app()

    with app.app_context():
        try:
            result = DocumentProcessingService.process_paper(
                paper_id
            )

            print("\n========== 论文处理成功 ==========")
            pprint(result, sort_dicts=False)

        except (DocumentProcessingError, ValueError) as exc:
            print("\n========== 论文处理失败 ==========")
            print(str(exc))


if __name__ == "__main__":
    main()
