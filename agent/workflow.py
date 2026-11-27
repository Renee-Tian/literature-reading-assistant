from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    qa_node,
    reading_node,
    research_node,
    route_next_agent,
    supervisor_node,
    synthesis_node,
)
from agent.state import LiteratureState


WORKFLOW_ROUTES = {
    "reading": "reading",
    "qa": "qa",
    "research": "research",
    "synthesis": "synthesis",
}


def build_workflow(checkpointer=None):
    """构建 Supervisor + 三个专业 Agent 的 LangGraph 工作流。"""

    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(LiteratureState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("reading", reading_node)
    builder.add_node("qa", qa_node)
    builder.add_node("research", research_node)
    builder.add_node("synthesis", synthesis_node)

    builder.add_edge(START, "supervisor")

    builder.add_conditional_edges(
        "supervisor",
        route_next_agent,
        WORKFLOW_ROUTES,
    )

    for agent_name in ("reading", "qa", "research"):
        builder.add_conditional_edges(
            agent_name,
            route_next_agent,
            WORKFLOW_ROUTES,
        )

    builder.add_edge("synthesis", END)

    return builder.compile(checkpointer=checkpointer)


checkpointer = MemorySaver()
workflow = build_workflow(checkpointer=checkpointer)


def build_initial_state(
    user_query,
    paper_ids,
    top_k=5,
    reading_max_chars=None,
    research_top_k=8,
):
    """初始化工作流 State。"""

    if not isinstance(user_query, str) or not user_query.strip():
        raise ValueError("用户问题不能为空。")

    if not isinstance(paper_ids, list) or not paper_ids:
        raise ValueError("paper_ids 必须是非空列表。")

    if len(paper_ids) != 1:
        raise ValueError(
            "当前三个专业 Agent 只支持单篇论文，"
            "请提供一个 paper_id。"
        )

    paper_id = paper_ids[0]

    if (
        not isinstance(paper_id, int)
        or isinstance(paper_id, bool)
        or paper_id <= 0
    ):
        raise ValueError("paper_id 必须是正整数。")

    normalized_query = user_query.strip()

    state = {
        "user_query": normalized_query,
        "resolved_query": normalized_query,
        "paper_ids": paper_ids,
        "top_k": top_k,
        "research_top_k": research_top_k,
        "task_plan": "",
        "next_agents": [],
        "reading_result": {},
        "qa_result": {},
        "research_result": {},
        "current_agent_index": 0,
        "completed_agents": [],
        "messages": [
            HumanMessage(content=normalized_query)
        ],
        "final_answer": "",
        "error": "",
    }

    if reading_max_chars is not None:
        state["reading_max_chars"] = reading_max_chars

    return state


def run_workflow(
    user_query,
    paper_ids,
    thread_id,
    top_k=5,
    reading_max_chars=None,
    research_top_k=8,
):
    """在指定会话中执行一次完整的 LangGraph 工作流。"""

    if (
        not isinstance(thread_id, str)
        or not thread_id.strip()
    ):
        raise ValueError("thread_id 必须是非空字符串。")

    initial_state = build_initial_state(
        user_query=user_query,
        paper_ids=paper_ids,
        top_k=top_k,
        reading_max_chars=reading_max_chars,
        research_top_k=research_top_k,
    )

    config = {
        "configurable": {
            "thread_id": thread_id.strip()
        }
    }

    final_state = None

    for snapshot in workflow.stream(
        initial_state,
        config=config,
        stream_mode="values",
    ):
        final_state = snapshot

    if final_state is None:
        raise ValueError(
            "LangGraph Workflow 没有返回有效的 State。"
        )

    return final_state


def get_thread_state(thread_id):
    """读取指定会话当前保存的 State。"""

    if (
        not isinstance(thread_id, str)
        or not thread_id.strip()
    ):
        raise ValueError("thread_id 必须是非空字符串。")

    config = {
        "configurable": {
            "thread_id": thread_id.strip()
        }
    }

    return workflow.get_state(config)
