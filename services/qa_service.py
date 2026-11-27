"""
学术文献问答协调服务。

职责：
1. 校验问答请求参数。
2. 调用 retrieval_service 完成 Dense + Sparse + RRF 检索。
3. 将检索结果整理成带编号的原文证据。
4. 构造 Prompt 并调用 llm_service 生成结构化回答。
5. 校验回答结构，并将引用绑定到真实检索证据。
6. 可选地保存问答历史。

本模块不实现 Embedding、向量检索或 LLM API 请求。
"""

from ai.llm_service import chat_completion_json, LLMError
from database.db import db
from models import Paper, QARecord
from rag.retrieval_service import retrieval_service, RetrievalError


class QAServiceError(Exception):
    """问答协调服务异常。"""
    pass


QA_PROMPT_VERSION = "1.0"

MAX_EVIDENCE_CHARS = 1600


QA_SYSTEM_PROMPT = """
你是一名严谨的学术论文问答助手。

请严格遵守以下规则：
1. 只能根据用户提供的“原文证据”回答问题。
2. 不得编造证据中不存在的信息。
3. 回答使用中文，语言简洁、准确。
4. 每个关键结论后面必须标注证据编号，例如 [E1]、[E2]。
5. 如果证据不足，请明确回答“根据现有证据无法回答该问题”。
6. 不要引用证据编号以外的内容。

请严格返回 JSON，格式如下：
{
    "answer": "中文回答正文",
    "citations": [
        {
            "evidence_id": "E1",
            "quote": "支持该结论的原文片段",
            "reason": "该原文为什么支持回答"
        }
    ]
}

说明：
- citations 中的 evidence_id 必须来自提供的证据编号。
- 如果证据不足，answer 说明无法回答，citations 返回空数组。
"""


def validate_question(question):
    """校验用户问题。"""

    if not isinstance(question, str) or not question.strip():
        raise QAServiceError("用户问题不能为空。")

    return question.strip()


def validate_paper_id(paper_id):
    """校验论文 ID。"""

    if (
        not isinstance(paper_id, int)
        or isinstance(paper_id, bool)
        or paper_id <= 0
    ):
        raise QAServiceError("paper_id 必须是正整数。")

    return paper_id


def validate_top_k(top_k):
    """校验检索数量。"""

    if (
        not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
    ):
        raise QAServiceError("top_k 必须是正整数。")

    return top_k


def get_paper_title(paper_id):
    """读取论文标题，同时确认论文存在。"""

    paper = db.session.get(Paper, paper_id)

    if paper is None:
        raise QAServiceError(
            f"论文不存在，paper_id={paper_id}。"
        )

    return paper.title


def build_evidence(retrieval_result):
    """将混合检索结果整理成带编号的证据列表。"""

    raw_results = retrieval_result.get("results") or []

    evidence = []

    for index, item in enumerate(raw_results, start=1):
        content = item.get("content") or ""

        evidence.append({
            "evidence_id": f"E{index}",
            "vector_id": item.get("id"),
            "paper_id": item.get("paper_id"),
            "chunk_index": item.get("chunk_index"),
            "page_number": item.get("page_number"),
            "content": content,
            "truncated_for_prompt": (
                len(content) > MAX_EVIDENCE_CHARS
            ),
            "rrf_score": item.get("rrf_score"),
            "dense_rank": item.get("dense_rank"),
            "sparse_rank": item.get("sparse_rank"),
            "sparse_score": item.get("sparse_score"),
            "retrieval_sources": item.get(
                "retrieval_sources",
                []
            )
        })

    return evidence


def build_qa_messages(question, paper_title, evidence):
    """构造问答任务所需的 messages。"""

    evidence_blocks = []

    for item in evidence:
        content = item["content"]

        if item["truncated_for_prompt"]:
            content = content[:MAX_EVIDENCE_CHARS] + "……"

        evidence_blocks.append(
            "\n".join([
                f"[{item['evidence_id']}]",
                f"论文 ID：{item['paper_id']}",
                f"Chunk 编号：{item['chunk_index']}",
                f"页码：{item['page_number']}",
                f"RRF 分数：{item['rrf_score']}",
                f"召回来源：{'、'.join(item['retrieval_sources'])}",
                f"原文：{content}"
            ])
        )

    user_content = "\n\n".join([
        f"论文标题：{paper_title or '未知'}",
        f"用户问题：{question}",
        "原文证据：",
        "\n\n".join(evidence_blocks)
    ])

    return [
        {
            "role": "system",
            "content": QA_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_content
        }
    ]


def validate_llm_answer(llm_data, evidence):
    """校验 LLM 结构化回答，并绑定真实证据。"""

    if not isinstance(llm_data, dict):
        raise QAServiceError(
            "LLM 返回的问答结果必须是 JSON 对象。"
        )

    answer = llm_data.get("answer")

    if not isinstance(answer, str) or not answer.strip():
        raise QAServiceError(
            "LLM 返回结果缺少有效的 answer 字段。"
        )

    raw_citations = llm_data.get("citations", [])

    if raw_citations is None:
        raw_citations = []

    if not isinstance(raw_citations, list):
        raise QAServiceError(
            "citations 必须是数组。"
        )

    evidence_map = {
        item["evidence_id"]: item
        for item in evidence
    }

    citations = []

    for raw in raw_citations:
        if not isinstance(raw, dict):
            raise QAServiceError(
                "citations 中的每一项必须是对象。"
            )

        evidence_id = raw.get("evidence_id")

        if evidence_id not in evidence_map:
            raise QAServiceError(
                f"回答引用了不存在的证据编号：{evidence_id}。"
            )

        quote = raw.get("quote") or ""
        reason = raw.get("reason") or ""

        if not isinstance(quote, str):
            raise QAServiceError(
                "citation.quote 必须是字符串。"
            )

        if not isinstance(reason, str):
            raise QAServiceError(
                "citation.reason 必须是字符串。"
            )

        source = evidence_map[evidence_id]

        citations.append({
            "evidence_id": evidence_id,
            "quote": quote.strip(),
            "reason": reason.strip(),
            "vector_id": source["vector_id"],
            "paper_id": source["paper_id"],
            "chunk_index": source["chunk_index"],
            "page_number": source["page_number"],
            "content": source["content"],
            "dense_rank": source["dense_rank"],
            "sparse_rank": source["sparse_rank"],
            "rrf_score": source["rrf_score"],
            "sparse_score": source["sparse_score"],
            "retrieval_sources": source[
                "retrieval_sources"
            ]
        })

    return answer.strip(), citations


def serialize_citation(citation):
    """精简引用内容后再写入数据库。"""

    return {
        "evidence_id": citation.get("evidence_id"),
        "quote": citation.get("quote"),
        "reason": citation.get("reason"),
        "vector_id": citation.get("vector_id"),
        "paper_id": citation.get("paper_id"),
        "chunk_index": citation.get("chunk_index"),
        "page_number": citation.get("page_number"),
        "dense_rank": citation.get("dense_rank"),
        "sparse_rank": citation.get("sparse_rank"),
        "rrf_score": citation.get("rrf_score"),
        "sparse_score": citation.get("sparse_score"),
        "retrieval_sources": citation.get(
            "retrieval_sources",
            []
        )
    }


def serialize_qa_record(record):
    """将问答记录模型转换为可返回的字典。"""

    return {
        "id": record.id,
        "paper_id": record.paper_id,
        "question": record.question,
        "answer": record.answer,
        "citations": record.citations,
        "created_at": (
            record.created_at.isoformat()
            if record.created_at
            else None
        )
    }


def save_qa_record(paper_id, question, answer, citations):
    """保存问答历史。"""

    try:
        record = QARecord(
            paper_id=paper_id,
            question=question,
            answer=answer,
            citations=[
                serialize_citation(item)
                for item in citations
            ]
        )

        db.session.add(record)
        db.session.commit()

        return record

    except Exception as error:
        db.session.rollback()

        raise QAServiceError(
            f"问答记录保存失败：{error}"
        ) from error


def build_retrieval_summary(retrieval_result):
    """提取检索调用信息，避免把原始检索结构直接暴露给上层。"""

    return {
        "search_mode": retrieval_result.get("search_mode"),
        "embedding_model": retrieval_result.get(
            "embedding_model"
        ),
        "query_dimensions": retrieval_result.get(
            "query_dimensions"
        ),
        "sparse_nonzero_count": retrieval_result.get(
            "sparse_nonzero_count"
        ),
        "query_tokens": retrieval_result.get(
            "query_tokens"
        ),
        "embedding_time_ms": retrieval_result.get(
            "embedding_time_ms"
        ),
        "result_count": retrieval_result.get(
            "result_count"
        )
    }


def answer_question(
    question,
    paper_id,
    top_k=5,
    save_history=True
):
    """
    执行一次完整的论文问答。

    流程：
    1. 参数校验
    2. Dense + Sparse + RRF 检索
    3. 证据整理
    4. LLM 生成结构化回答
    5. 引用绑定
    6. 历史持久化
    """

    question = validate_question(question)
    paper_id = validate_paper_id(paper_id)
    top_k = validate_top_k(top_k)

    if not isinstance(save_history, bool):
        raise QAServiceError(
            "save_history 必须是布尔值。"
        )

    paper_title = get_paper_title(paper_id)

    try:
        retrieval_result = retrieval_service.search(
            question=question,
            paper_id=paper_id,
            top_k=top_k
        )

    except RetrievalError as error:
        raise QAServiceError(
            f"问答检索失败：{error}"
        ) from error

    evidence = build_evidence(retrieval_result)
    retrieval_summary = build_retrieval_summary(
        retrieval_result
    )

    if not evidence:
        answer = (
            "根据现有证据无法回答该问题。"
            "当前论文未检索到相关原文片段，"
            "请先完成论文向量化入库，或尝试调整问题表述。"
        )

        record = None

        if save_history:
            record = save_qa_record(
                paper_id,
                question,
                answer,
                []
            )

        return {
            "question": question,
            "paper_id": paper_id,
            "paper_title": paper_title,
            "answer": answer,
            "citations": [],
            "evidence": [],
            "retrieval": retrieval_summary,
            "llm": None,
            "qa_record": (
                serialize_qa_record(record)
                if record
                else None
            )
        }

    messages = build_qa_messages(
        question,
        paper_title,
        evidence
    )

    try:
        llm_result = chat_completion_json(
            messages=messages,
            temperature=0.1
        )

        answer, citations = validate_llm_answer(
            llm_result.get("data"),
            evidence
        )

    except LLMError as error:
        raise QAServiceError(
            f"问答回答生成失败：{error}"
        ) from error

    record = None

    if save_history:
        record = save_qa_record(
            paper_id,
            question,
            answer,
            citations
        )

    return {
        "question": question,
        "paper_id": paper_id,
        "paper_title": paper_title,
        "answer": answer,
        "citations": citations,
        "evidence": evidence,
        "retrieval": retrieval_summary,
        "llm": {
            "model": llm_result.get("model"),
            "usage": llm_result.get("usage"),
            "elapsed_ms": llm_result.get("elapsed_ms"),
            "request_id": llm_result.get("request_id"),
            "prompt_version": QA_PROMPT_VERSION
        },
        "qa_record": (
            serialize_qa_record(record)
            if record
            else None
        )
    }


def list_qa_history(paper_id, limit=20):
    """获取指定论文的问答历史。"""

    paper_id = validate_paper_id(paper_id)

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit <= 0
    ):
        raise QAServiceError(
            "limit 必须是正整数。"
        )

    paper = db.session.get(Paper, paper_id)

    if paper is None:
        raise QAServiceError(
            f"论文不存在，paper_id={paper_id}。"
        )

    records = (
        db.session.query(QARecord)
        .filter(QARecord.paper_id == paper_id)
        .order_by(QARecord.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        serialize_qa_record(record)
        for record in records
    ]


class QAService:
    """问答服务类形式入口。"""

    @staticmethod
    def answer(
        question,
        paper_id,
        top_k=5,
        save_history=True
    ):
        return answer_question(
            question=question,
            paper_id=paper_id,
            top_k=top_k,
            save_history=save_history
        )

    @staticmethod
    def list_history(paper_id, limit=20):
        return list_qa_history(
            paper_id=paper_id,
            limit=limit
        )


qa_service = QAService()
