from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class LiteratureState(TypedDict, total=False):
    """Supervisor 与三个专业 Agent 共享的状态。"""

    # Supervisor 输入与规划字段
    user_query: str
    resolved_query: str
    paper_ids: List[int]
    task_plan: str
    next_agents: List[str]

    # Reading Agent：论文整体阅读与内容概括
    reading_result: Dict[str, Any]

    # QA Agent：知识检索、问答与原文证据定位
    qa_result: Dict[str, Any]

    # Research Agent：研究方法、算法、实验设计与结果分析
    research_result: Dict[str, Any]

    # LangGraph 执行进度
    current_agent_index: int
    completed_agents: List[str]

    # Agent 执行过程中的通用字段
    # add_messages 会把每轮输入和最终回答追加到历史中
    messages: Annotated[List[AnyMessage], add_messages]
    final_answer: str
    error: str
