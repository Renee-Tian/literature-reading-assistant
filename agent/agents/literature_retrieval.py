"""
旧版文献检索 Agent 兼容层。

检索、问答和证据定位能力已经迁移到 qa_agent。
保留本文件是为了避免已有导入立即失效，
新代码应直接使用 agent.agents.qa_agent.qa_agent。
"""

from .qa_agent import (
    QAAgentError,
    qa_agent,
)


LiteratureRetrievalError = QAAgentError


def literature_retrieval_agent(state):
    """兼容旧入口，实际执行 QA Agent。"""

    return qa_agent(state)
