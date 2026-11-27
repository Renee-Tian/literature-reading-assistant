from ai.llm_service import chat_completion_json, LLMError
from rag.retrieval_service import retrieval_service, RetrievalError
from services.qa_service import build_evidence


class ResearchAgentError(Exception):
    """Research Agent 异常。"""
    pass


MAX_EVIDENCE_CHARS = 1600

REQUIRED_STRING_FIELDS = [
    "research_problem",
    "methodology",
    "experimental_design",
    "results",
]

REQUIRED_LIST_FIELDS = [
    "algorithms",
    "datasets",
    "metrics",
    "contributions",
    "limitations",
    "evidence_ids",
]


RESEARCH_SYSTEM_PROMPT = """
你是一名严谨的学术论文研究分析助手。

你的任务是根据提供的论文原文证据，
分析论文的研究方法、算法、实验设计和结果。

必须遵守以下规则：
1. 只能依据提供的原文证据进行分析。
2. 不得编造原文中没有的方法、数据集、指标或数值。
3. 信息不足时，明确写“原文未说明”。
4. 每个关键结论后标注证据编号，例如 [E1]。
5. 使用中文回答。
6. 不要引用不存在的证据编号。

请严格返回以下 JSON：

{
    "research_problem": "论文要解决的研究问题",
    "methodology": "研究方法与技术路线",
    "algorithms": [
        "涉及的算法或模型"
    ],
    "experimental_design": "实验设计说明",
    "datasets": [
        "数据集"
    ],
    "metrics": [
        "评价指标"
    ],
    "results": "主要实验结果与结论",
    "contributions": [
        "主要贡献"
    ],
    "limitations": [
        "局限性"
    ],
    "evidence_ids": [
        "E1",
        "E2"
    ]
}
"""


def get_single_paper_id(state):
    """读取并校验论文 ID。"""

    paper_ids = state.get("paper_ids") or []

    if not isinstance(paper_ids, list):
        raise ResearchAgentError("paper_ids 必须是列表。")

    if len(paper_ids) != 1:
        raise ResearchAgentError(
            "Research Agent 当前只支持一篇论文，请提供一个 paper_id。"
        )

    paper_id = paper_ids[0]

    if (
        not isinstance(paper_id, int)
        or isinstance(paper_id, bool)
        or paper_id <= 0
    ):
        raise ResearchAgentError("paper_id 必须是正整数。")

    return paper_id


def get_research_evidence(state, paper_id, user_query):
    """优先复用 QA 证据，否则执行一次研究导向的检索。"""

    qa_result = state.get("qa_result")

    if isinstance(qa_result, dict):
        evidence = qa_result.get("evidence")

        if isinstance(evidence, list) and evidence:
            return evidence

    legacy_evidence = state.get("retrieval_result")

    if isinstance(legacy_evidence, list) and legacy_evidence:
        return legacy_evidence

    research_query = (
        f"{user_query}\n"
        "请重点检索研究方法、算法、模型结构、实验设计、"
        "数据集、评价指标、实验结果和局限性。"
    )

    try:
        retrieval_result = retrieval_service.search(
            question=research_query,
            paper_id=paper_id,
            top_k=state.get("research_top_k", 8),
        )

    except RetrievalError as error:
        raise ResearchAgentError(
            f"Research Agent 检索失败：{error}"
        ) from error

    return build_evidence(retrieval_result)


def build_research_messages(user_query, evidence):
    """构造研究分析 Prompt。"""

    evidence_blocks = []

    for item in evidence:
        content = item.get("content", "")

        if len(content) > MAX_EVIDENCE_CHARS:
            content = content[:MAX_EVIDENCE_CHARS] + "……"

        evidence_blocks.append(
            "\n".join([
                f"[{item.get('evidence_id')}]",
                f"页码：{item.get('page_number')}",
                f"Chunk 编号：{item.get('chunk_index')}",
                f"原文：{content}",
            ])
        )

    user_content = "\n\n".join([
        f"用户任务：{user_query}",
        "论文原文证据：",
        "\n\n".join(evidence_blocks),
    ])

    return [
        {
            "role": "system",
            "content": RESEARCH_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]


def validate_research_result(data, evidence):
    """校验研究分析结果，并检查证据编号。"""

    if not isinstance(data, dict):
        raise ResearchAgentError(
            "Research Agent 返回结果必须是 JSON 对象。"
        )

    for field in REQUIRED_STRING_FIELDS:
        value = data.get(field)

        if not isinstance(value, str) or not value.strip():
            raise ResearchAgentError(
                f"研究分析缺少有效字段：{field}"
            )

    for field in REQUIRED_LIST_FIELDS:
        value = data.get(field)

        if not isinstance(value, list):
            raise ResearchAgentError(
                f"研究分析字段 {field} 必须是列表。"
            )

        if not all(isinstance(item, str) for item in value):
            raise ResearchAgentError(
                f"研究分析字段 {field} 必须只包含字符串。"
            )

    evidence_ids = {
        item.get("evidence_id")
        for item in evidence
    }

    invalid_ids = set(data["evidence_ids"]) - evidence_ids

    if invalid_ids:
        raise ResearchAgentError(
            f"研究分析引用了不存在的证据：{invalid_ids}"
        )

    return {
        "research_problem": data["research_problem"].strip(),
        "methodology": data["methodology"].strip(),
        "algorithms": data["algorithms"],
        "experimental_design": data["experimental_design"].strip(),
        "datasets": data["datasets"],
        "metrics": data["metrics"],
        "results": data["results"].strip(),
        "contributions": data["contributions"],
        "limitations": data["limitations"],
        "evidence_ids": data["evidence_ids"],
    }


def research_agent(state):
    """
    Research Agent。

    负责：
    1. 复用 QA 检索证据，或执行研究导向检索。
    2. 调用 LLM 分析方法、算法、实验和结果。
    3. 返回结构化研究分析结果。
    """

    user_query = state.get("user_query", "").strip()

    if not user_query:
        raise ResearchAgentError("用户问题不能为空。")

    resolved_query = (
        state.get("resolved_query") or user_query
    ).strip()

    paper_id = get_single_paper_id(state)

    evidence = get_research_evidence(
        state=state,
        paper_id=paper_id,
        user_query=resolved_query,
    )

    if not evidence:
        raise ResearchAgentError(
            "没有检索到可用于研究分析的原文证据。"
        )

    messages = build_research_messages(
        user_query=resolved_query,
        evidence=evidence,
    )

    try:
        result = chat_completion_json(
            messages=messages,
            temperature=0.1,
        )

    except LLMError as error:
        raise ResearchAgentError(
            f"Research Agent LLM 调用失败：{error}"
        ) from error

    analysis = validate_research_result(
        result["data"],
        evidence,
    )

    return {
        "research_result": {
            "paper_id": paper_id,
            "analysis": analysis,
            "evidence": evidence,
            "model": result.get("model"),
            "usage": result.get("usage"),
            "elapsed_ms": result.get("elapsed_ms"),
            "request_id": result.get("request_id"),
        }
    }
