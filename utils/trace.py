import json
import logging
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4


_trace_context = ContextVar("agent_trace", default=None)


def utc_now():
    """返回 UTC ISO 时间。"""

    return datetime.now(timezone.utc).isoformat()


def elapsed_ms(start_time):
    """将 perf_counter 差值转换为毫秒。"""

    return round(
        (time.perf_counter() - start_time) * 1000,
        2,
    )


class TraceSpan:
    """记录单个 Workflow 节点的开始、结束和耗时。"""

    def __init__(
        self,
        recorder,
        name,
        kind="agent",
        attributes=None,
    ):
        self.recorder = recorder
        self.name = name
        self.kind = kind
        self.attributes = attributes or {}
        self.started_at = None
        self.finished_at = None
        self.started_perf = None
        self.elapsed_ms = None

    def set(self, key, value):
        self.attributes[key] = value
        return self

    def __enter__(self):

        self.started_at = utc_now()
        self.started_perf = time.perf_counter()

        self.recorder.span_stack.append(self.name)

        return self

    def __exit__(self, exc_type, exc, traceback):

        self.finished_at = utc_now()
        self.elapsed_ms = elapsed_ms(self.started_perf)

        if (
            self.recorder.span_stack
            and self.recorder.span_stack[-1] == self.name
        ):
            self.recorder.span_stack.pop()

        if exc is not None:
            status = "failed"
            self.attributes["error"] = str(exc)
            self.recorder.add_error(exc)
        else:
            status = "success"

        self.recorder.add_span({
            "name": self.name,
            "kind": self.kind,
            "status": status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_ms": self.elapsed_ms,
            "attributes": self.attributes,
        })

        return False


class TraceRecorder:
    """保存一次请求的结构化执行轨迹。"""

    def __init__(self, question, thread_id, paper_ids):
        self.request_id = str(uuid4())
        self.thread_id = thread_id
        self.question = question
        self.paper_ids = paper_ids
        self.started_at = utc_now()
        self.started_perf = time.perf_counter()
        self.finished = False

        self.spans = []
        self.llm_calls = []
        self.retrieval_calls = []
        self.errors = []
        self.span_stack = []

    def span(self, name, kind="agent", attributes=None):
        return TraceSpan(
            recorder=self,
            name=name,
            kind=kind,
            attributes=attributes,
        )

    def current_span_name(self):
        if not self.span_stack:
            return "workflow"

        return self.span_stack[-1]

    def add_span(self, span):
        self.spans.append(span)

    def add_error(self, error):

        self.errors.append({
            "timestamp": utc_now(),
            "agent": self.current_span_name(),
            "type": type(error).__name__,
            "message": str(error),
        })

    def add_llm_call(self, data):

        item = {
            "sequence": len(self.llm_calls) + 1,
            "timestamp": utc_now(),
            "agent": self.current_span_name(),
        }

        item.update(data)
        self.llm_calls.append(item)

    def add_retrieval_call(self, data):

        item = {
            "sequence": len(self.retrieval_calls) + 1,
            "timestamp": utc_now(),
            "agent": self.current_span_name(),
        }

        item.update(data)
        self.retrieval_calls.append(item)

    def finish(
        self,
        status="success",
        error=None,
        final_state=None,
    ):
        """汇总本次请求并写入 JSONL。"""

        if self.finished:
            return None

        self.finished = True
        finished_at = utc_now()
        total_elapsed_ms = elapsed_ms(self.started_perf)

        if error and not self.errors:
            self.errors.append({
                "timestamp": finished_at,
                "agent": "workflow",
                "type": type(error).__name__,
                "message": str(error),
            })

        agent_spans = [
            span
            for span in self.spans
            if span["kind"] == "agent"
        ]

        supervisor_span = next(
            (
                span
                for span in self.spans
                if span["name"] == "supervisor"
            ),
            None,
        )

        supervisor_summary = None

        if supervisor_span is not None:
            attributes = supervisor_span["attributes"]

            supervisor_summary = {
                "status": supervisor_span["status"],
                "started_at": supervisor_span["started_at"],
                "finished_at": supervisor_span["finished_at"],
                "elapsed_ms": supervisor_span["elapsed_ms"],
                "task_plan": attributes.get("task_plan"),
                "resolved_query": attributes.get(
                    "resolved_query"
                ),
                "next_agents": attributes.get(
                    "next_agents",
                    [],
                ),
            }

        prompt_tokens = sum(
            (item.get("prompt_tokens") or 0)
            for item in self.llm_calls
        )

        completion_tokens = sum(
            (item.get("completion_tokens") or 0)
            for item in self.llm_calls
        )

        total_tokens = sum(
            (item.get("total_tokens") or 0)
            for item in self.llm_calls
        )

        success_agents = sum(
            1
            for span in agent_spans
            if span["status"] == "success"
        )

        failed_agents = sum(
            1
            for span in agent_spans
            if span["status"] == "failed"
        )

        final_answer = ""

        if isinstance(final_state, dict):
            final_answer = final_state.get(
                "final_answer",
                "",
            ) or ""

        record = {
            "request_id": self.request_id,
            "thread_id": self.thread_id,
            "question": self.question,
            "paper_ids": self.paper_ids,
            "status": status,
            "started_at": self.started_at,
            "finished_at": finished_at,
            "total_elapsed_ms": total_elapsed_ms,
            "supervisor": supervisor_summary,
            "agents": agent_spans,
            "spans": self.spans,
            "llm_calls": self.llm_calls,
            "retrieval_calls": self.retrieval_calls,
            "errors": self.errors,
            "summary": {
                "total_elapsed_ms": total_elapsed_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "llm_call_count": len(self.llm_calls),
                "retrieval_call_count": len(
                    self.retrieval_calls
                ),
                "agent_count": len(agent_spans),
                "success_agent_count": success_agents,
                "failed_agent_count": failed_agents,
                "error_count": len(self.errors),
                "final_answer_length": len(final_answer),
            },
        }

        trace_logger = logging.getLogger("agent_trace")
        trace_logger.info(
            json.dumps(
                record,
                ensure_ascii=False,
                default=str,
            )
        )

        logging.getLogger(__name__).info(
            "agent request completed | request_id=%s | "
            "thread_id=%s | status=%s | elapsed_ms=%s | "
            "tokens=%s",
            self.request_id,
            self.thread_id,
            status,
            total_elapsed_ms,
            total_tokens,
        )

        return record


def start_trace(question, thread_id, paper_ids):
    """创建并绑定当前请求的 TraceRecorder。"""

    recorder = TraceRecorder(
        question=question,
        thread_id=thread_id,
        paper_ids=paper_ids,
    )

    _trace_context.set(recorder)

    return recorder


def get_trace():
    """获取当前请求的 TraceRecorder。"""

    return _trace_context.get()


def finish_trace(
    status="success",
    error=None,
    final_state=None,
):
    """结束当前请求并写入 JSONL。"""

    recorder = get_trace()

    if recorder is None:
        return None

    record = recorder.finish(
        status=status,
        error=error,
        final_state=final_state,
    )

    _trace_context.set(None)

    return record


class NullSpan:
    """没有 Trace 时使用的空 Span。"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def set(self, key, value):
        return self


def trace_span(name, kind="agent", attributes=None):
    """创建当前请求的节点 Span；无 Trace 时返回空 Span。"""

    recorder = get_trace()

    if recorder is None:
        return NullSpan()

    return recorder.span(
        name=name,
        kind=kind,
        attributes=attributes,
    )


def record_llm_call(data):
    """记录一次 LLM 调用。"""

    recorder = get_trace()

    if recorder is not None:
        recorder.add_llm_call(data)


def record_retrieval_call(data):
    """记录一次 RAG 检索调用。"""

    recorder = get_trace()

    if recorder is not None:
        recorder.add_retrieval_call(data)
