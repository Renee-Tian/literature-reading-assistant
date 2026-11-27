"""
前端页面与接口联调验收脚本。

运行方式（在项目根目录执行）：

    .venv\\Scripts\\python.exe tests\\manual_test_frontend.py

检查内容：
1. 六个页面渲染状态与关键元素。
2. 侧边导航激活项是否正确。
3. 静态资源（含本地 vendor）是否可访问。
4. 只读 API 是否返回预期状态。
5. 首页统计与论文列表数量是否一致。

本脚本只读取数据，不触发解析、向量化、问答或删除。
"""

import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from app import create_app  # noqa: E402


PAGES = [
    {
        "path": "/",
        "name": "工作台首页",
        "elements": ["stat-grid", "recentPapers", "serviceStatus", "js/dashboard.js"],
        "active": "工作台首页",
    },
    {
        "path": "/papers",
        "name": "论文管理",
        "elements": ["uploadForm", "papersTableWrap", "editModal", "js/papers.js"],
        "active": "论文管理",
    },
    {
        "path": "/papers/1/reader",
        "name": "智能阅读",
        "elements": ["pdfCanvas", "reportSection", "data-paper-id", "vendor/pdfjs/pdf.min.js"],
        "active": "论文管理",
    },
    {
        "path": "/chat",
        "name": "智能问答",
        "elements": ["paperSelect", "qaForm", "historyList", "js/chat.js"],
        "active": "智能问答",
    },
    {
        "path": "/research",
        "name": "研究分析",
        "elements": ["researchForm", "researchResult", "js/research.js"],
        "active": "研究分析",
    },
    {
        "path": "/agents",
        "name": "Agent 协作",
        "elements": ["agentsForm", "agentsResult", "threadIdLabel", "js/agents.js"],
        "active": "Agent 协作",
    },
]


STATIC_ASSETS = [
    "/static/css/app.css",
    "/static/js/api.js",
    "/static/js/layout.js",
    "/static/js/dashboard.js",
    "/static/js/papers.js",
    "/static/js/reader.js",
    "/static/js/chat.js",
    "/static/js/research.js",
    "/static/js/agents.js",
    "/static/vendor/bootstrap/bootstrap.min.css",
    "/static/vendor/bootstrap/bootstrap.bundle.min.js",
    "/static/vendor/pdfjs/pdf.min.js",
    "/static/vendor/pdfjs/pdf.worker.min.js",
]


API_ENDPOINTS = [
    "/api/health",
    "/api/db-health",
    "/api/system/stats",
    "/api/papers/?limit=100",
]


JS_CHECKS = [
    ("/", "static/js/dashboard.js"),
    ("/papers", "static/js/papers.js"),
    ("/papers/1/reader", "static/js/reader.js"),
    ("/chat", "static/js/chat.js"),
    ("/research", "static/js/research.js"),
    ("/agents", "static/js/agents.js"),
]


# 由脚本动态创建、不来自模板的 id
DYNAMIC_IDS = {"qaLoading"}


class Checker:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def ok(self, message):
        self.passed += 1
        print("[PASS]", message)

    def fail(self, message):
        self.failed += 1
        print("[FAIL]", message)

    def skip(self, message):
        self.skipped += 1
        print("[SKIP]", message)

    def expect(self, condition, message):
        if condition:
            self.ok(message)
        else:
            self.fail(message)


def extract_active_labels(html):
    """提取侧边栏中所有激活项的文字。"""

    return [
        match.strip()
        for match in re.findall(
            r'class="app-nav-item is-active"[^>]*>.*?<span>([^<]+)</span>',
            html,
            re.S,
        )
    ]


def main():
    app = create_app()
    client = app.test_client()
    checker = Checker()

    print("=" * 64)
    print("Literature AI 前端联调验收")
    print("=" * 64)

    # 1. 页面渲染与导航
    print("\n-- 页面渲染与导航 --")

    for page in PAGES:
        response = client.get(page["path"])
        html = response.get_data(as_text=True)

        checker.expect(
            response.status_code == 200,
            f'{page["path"]} 返回 200（{page["name"]}）',
        )

        missing = [item for item in page["elements"] if item not in html]
        checker.expect(
            not missing,
            f'{page["path"]} 关键元素齐全'
            + (f"，缺失：{missing}" if missing else ""),
        )

        active_labels = extract_active_labels(html)
        checker.expect(
            page["active"] in active_labels,
            f'{page["path"]} 导航激活项为「{page["active"]}」'
            + (f"（实际：{active_labels}）" if page["active"] not in active_labels else ""),
        )

        checker.expect(
            "viewport" in html,
            f'{page["path"]} 包含 viewport 声明',
        )

    # 2. 静态资源
    print("\n-- 静态资源 --")

    for asset in STATIC_ASSETS:
        response = client.get(asset)
        checker.expect(
            response.status_code == 200 and len(response.data) > 0,
            f"{asset} 可访问（{len(response.data)} 字节）",
        )

    # 3. 只读接口
    print("\n-- 只读接口 --")

    for endpoint in API_ENDPOINTS:
        response = client.get(endpoint)
        payload = response.get_json(silent=True) or {}

        checker.expect(
            response.status_code == 200,
            f"{endpoint} 返回 200（实际 {response.status_code}）",
        )

        checker.expect(
            payload.get("status") in {"ok", "success"},
            f"{endpoint} 返回可识别的 status",
        )

    # 4. 统计与列表一致性
    print("\n-- 数据一致性 --")

    stats_response = client.get("/api/system/stats")

    if stats_response.status_code != 200:
        checker.skip("统计接口不可用，跳过一致性检查（请检查数据库连接）")
    else:
        stats = (stats_response.get_json() or {}).get("data") or {}
        papers_payload = client.get("/api/papers/?limit=100").get_json() or {}

        paper_total = stats.get("paper_total")
        list_total = papers_payload.get("total")

        if isinstance(paper_total, int) and isinstance(list_total, int):
            if paper_total <= 100:
                checker.expect(
                    paper_total == list_total,
                    f"统计论文总数 {paper_total} 与列表数量 {list_total} 一致",
                )
            else:
                checker.ok(
                    f"论文总数 {paper_total} 超过列表上限 100，跳过数量一致比较"
                )
        else:
            checker.fail("统计或列表缺少论文总数")

        status_map = stats.get("paper_status") or {}
        status_sum = sum(
            value for value in status_map.values()
            if isinstance(value, int)
        )

        checker.expect(
            status_sum == paper_total,
            f"状态分布合计 {status_sum} 等于论文总数 {paper_total}",
        )

        checker.expect(
            stats.get("vector_total") is not None
            or bool(stats.get("vector_error")),
            "向量库统计返回数值或明确错误信息",
        )

    # 5. 页面与脚本的 DOM id 一致性
    print("\n-- DOM id 一致性 --")

    layout_js = (BASE_DIR / "static/js/layout.js").read_text(encoding="utf-8")
    layout_ids = set(
        re.findall(r'getElementById\(["\']([^"\']+)["\']\)', layout_js)
    )

    for page_path, js_path in JS_CHECKS:
        html = client.get(page_path).get_data(as_text=True)
        script = (BASE_DIR / js_path).read_text(encoding="utf-8")

        html_ids = set(re.findall(r'\bid="([^"]+)"', html))
        script_ids = set(
            re.findall(r'getElementById\(["\']([^"\']+)["\']\)', script)
        )
        script_ids |= layout_ids
        script_ids -= DYNAMIC_IDS

        missing = sorted(script_ids - html_ids)

        checker.expect(
            not missing,
            f"{page_path} 引用的 DOM id 全部存在"
            + (f"，缺失：{missing}" if missing else ""),
        )

    # 6. 404 行为
    print("\n-- 异常状态 --")

    checker.expect(
        client.get("/not-exist-page").status_code == 404,
        "未知页面返回 404",
    )

    checker.expect(
        client.get("/api/papers/999999").status_code == 404,
        "不存在的论文返回 404",
    )

    checker.expect(
        client.get("/api/papers/999999/reading-report/latest").status_code == 404,
        "不存在的论文阅读报告返回 404",
    )

    # 汇总
    print("\n" + "=" * 64)
    print(
        f"汇总：通过 {checker.passed} 项，失败 {checker.failed} 项，"
        f"跳过 {checker.skipped} 项"
    )
    print("=" * 64)

    return 0 if checker.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
