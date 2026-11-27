from agent.agents.reading_agent import reading_agent
from agent.agents.qa_agent import qa_agent
from agent.agents.research_agent import research_agent
from agent.agents.supervisor import (
    supervisor_agent,
    supervisor_synthesis_agent,
)
from utils.trace import trace_span


PROFESSIONAL_AGENTS = {
    "reading",
    "qa",
    "research",
}


def advance_state(state, agent_name, result):
    """写回专业 Agent 结果，并推进执行位置。"""

    index = state.get("current_agent_index", 0)

    if not isinstance(index, int) or index < 0:
        index = 0

    completed_agents = list(
        state.get("completed_agents") or []
    )

    completed_agents.append(agent_name)

    return {
        **result,
        "current_agent_index": index + 1,
        "completed_agents": completed_agents,
    }


def supervisor_node(state):
    """Supervisor 规划节点。"""

    with trace_span(
        "supervisor",
        kind="supervisor",
    ) as span:

        decision = supervisor_agent(state)

        span.set(
            "task_plan",
            decision.get("task_plan"),
        )
        span.set(
            "resolved_query",
            decision.get("resolved_query"),
        )
        span.set(
            "next_agents",
            decision.get("next_agents", []),
        )

    return {
        **decision,
        "current_agent_index": 0,
        "completed_agents": [],
    }


def reading_node(state):
    """Reading Agent 节点。"""

    with trace_span(
        "reading",
        kind="agent",
    ) as span:

        result = reading_agent(state)
        reading_result = result.get("reading_result") or {}

        span.set(
            "paper_id",
            reading_result.get("paper_id"),
        )
        span.set(
            "chunk_count",
            reading_result.get("chunk_count"),
        )
        span.set(
            "batch_count",
            reading_result.get("batch_count"),
        )

    return advance_state(
        state,
        "reading",
        result,
    )


def qa_node(state):
    """QA Agent 节点。"""

    with trace_span(
        "qa",
        kind="agent",
    ) as span:

        result = qa_agent(state)
        qa_result = result.get("qa_result") or {}

        citations = qa_result.get("citations") or []
        retrieval = qa_result.get("retrieval") or {}

        span.set(
            "answer_length",
            len(qa_result.get("answer") or ""),
        )
        span.set(
            "citation_count",
            len(citations),
        )
        span.set(
            "search_mode",
            retrieval.get("search_mode"),
        )
        span.set(
            "result_count",
            retrieval.get("result_count"),
        )

    return advance_state(
        state,
        "qa",
        result,
    )


def research_node(state):
    """Research Agent 节点。"""

    with trace_span(
        "research",
        kind="agent",
    ) as span:

        result = research_agent(state)
        research_result = result.get("research_result") or {}
        analysis = research_result.get("analysis") or {}

        span.set(
            "analysis_fields",
            sorted(analysis.keys()),
        )
        span.set(
            "evidence_count",
            len(research_result.get("evidence") or []),
        )

    return advance_state(
        state,
        "research",
        result,
    )


def synthesis_node(state):
    """Supervisor 最终整合节点。"""

    with trace_span(
        "synthesis",
        kind="supervisor",
    ) as span:

        result = supervisor_synthesis_agent(state)

        span.set(
            "final_answer_length",
            len(result.get("final_answer") or ""),
        )

    return result


def route_next_agent(state):
    """根据 Supervisor 计划和当前进度选择下一个节点。"""

    next_agents = state.get("next_agents") or []

    if not isinstance(next_agents, list):
        return "synthesis"

    index = state.get("current_agent_index", 0)

    if not isinstance(index, int) or index < 0:
        return "synthesis"

    if index >= len(next_agents):
        return "synthesis"

    agent_name = next_agents[index]

    if agent_name not in PROFESSIONAL_AGENTS:
        return "synthesis"

    return agent_name
