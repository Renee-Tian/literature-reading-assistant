/**
 * Agent 协作页面。
 *
 * 唯一数据入口：POST /api/agent/ask
 * - 所有状态均来自返回体：task_plan / next_agents / completed_agents / 各 Agent 结果。
 * - 不做流式进度模拟，等待期间只显示整体执行提示。
 */
(function () {
    "use strict";

    var AGENT_META = {
        reading: {
            name: "Reading Agent",
            desc: "论文整体阅读与内容概括"
        },
        qa: {
            name: "QA Agent",
            desc: "论文知识检索、问答与原文证据定位"
        },
        research: {
            name: "Research Agent",
            desc: "研究方法、算法、实验设计与结果分析"
        }
    };

    var state = {
        papers: [],
        paperId: null,
        threadId: "",
        busy: false,
        records: []
    };

    /* ============================ 基础工具 ============================ */

    function el(tag, className, text) {
        var node = document.createElement(tag);

        if (className) {
            node.className = className;
        }

        if (text !== undefined && text !== null) {
            node.textContent = String(text);
        }

        return node;
    }

    function api() {
        if (!window.LitApi) {
            throw new Error("请求模块未加载");
        }

        return window.LitApi;
    }

    function showAlert(message) {
        var box = document.getElementById("agentsAlert");
        var text = document.getElementById("agentsAlertText");

        if (box && text) {
            text.textContent = message;
            box.classList.add("is-visible");
        }
    }

    function hideAlert() {
        var box = document.getElementById("agentsAlert");

        if (box) {
            box.classList.remove("is-visible");
        }
    }

    function showNotice(title, text) {
        var box = document.getElementById("agentsNotice");
        var titleNode = document.getElementById("agentsNoticeTitle");
        var textNode = document.getElementById("agentsNoticeText");

        if (!box || !titleNode || !textNode) {
            return;
        }

        titleNode.textContent = title;
        textNode.textContent = text;
        box.classList.add("is-visible");
    }

    function hideNotice() {
        var box = document.getElementById("agentsNotice");

        if (box) {
            box.classList.remove("is-visible");
        }
    }

    function setBusy(busy) {
        state.busy = busy;

        var button = document.getElementById("agentsSubmitBtn");

        if (button) {
            button.disabled = busy;
            button.textContent = busy ? "执行中…" : "执行工作流";
        }
    }

    function createThreadId() {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }

        return "thread-" + Date.now() + "-" + Math.random().toString(16).slice(2, 10);
    }

    function updateThreadLabel() {
        var label = document.getElementById("threadIdLabel");

        if (label) {
            label.textContent = state.threadId || "—";
        }
    }

    function formatTime(iso) {
        if (!iso) {
            return "—";
        }

        var date = new Date(iso);

        if (Number.isNaN(date.getTime())) {
            return String(iso);
        }

        function pad(value) {
            return value < 10 ? "0" + value : String(value);
        }

        return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate())
            + " " + pad(date.getHours()) + ":" + pad(date.getMinutes());
    }

    /* ============================ 论文加载 ============================ */

    function loadPapers() {
        var select = document.getElementById("agentsPaperSelect");

        api().get("/api/papers/?limit=100", { timeout: 20000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !Array.isArray(payload.data)) {
                    throw new Error((payload && payload.message) || "论文列表返回格式异常");
                }

                state.papers = payload.data;
                select.textContent = "";

                if (state.papers.length === 0) {
                    select.appendChild(el("option", null, "还没有论文"));
                    select.disabled = true;
                    showAlert("请先在论文管理上传并解析 PDF。");
                    return;
                }

                state.papers.forEach(function (paper) {
                    var option = el("option", null, paper.title + "（#" + paper.id + "）");
                    option.value = String(paper.id);
                    select.appendChild(option);
                });

                state.paperId = state.papers[0].id;
            })
            .catch(function (error) {
                select.textContent = "";
                select.appendChild(el("option", null, "论文列表加载失败"));
                showAlert(error && error.message ? error.message : "论文列表加载失败");
            });
    }

    /* ============================ 结果渲染 ============================ */

    function resultHost() {
        return document.getElementById("agentsResult");
    }

    function resetResult(emptyText) {
        var host = resultHost();
        host.textContent = "";
        host.appendChild(el("div", "empty-state", emptyText));
    }

    function buildPipeline(data) {
        var nextAgents = Array.isArray(data.next_agents) ? data.next_agents : [];
        var completed = Array.isArray(data.completed_agents) ? data.completed_agents : [];
        var wrapper = el("div", "agent-pipeline");

        var stages = [
            {
                key: "supervisor",
                label: "Supervisor",
                done: Boolean(data.task_plan)
            }
        ].concat(nextAgents.map(function (name) {
            return {
                key: name,
                label: (AGENT_META[name] && AGENT_META[name].name) || name,
                done: completed.indexOf(name) !== -1
            };
        })).concat([
            {
                key: "synthesis",
                label: "汇总整合",
                done: Boolean(data.final_answer)
            }
        ]);

        stages.forEach(function (stage, index) {
            if (index > 0) {
                wrapper.appendChild(el("span", "agent-arrow", "→"));
            }

            var node = el(
                "span",
                "agent-node " + (stage.done ? "is-done" : "is-idle"),
                stage.label
            );

            wrapper.appendChild(node);
        });

        return wrapper;
    }

    function buildMetaRows(rows) {
        var list = el("dl", "meta-list");

        rows.forEach(function (row) {
            if (row[1] === null || row[1] === undefined || row[1] === "") {
                return;
            }

            list.appendChild(el("dt", null, row[0]));
            list.appendChild(el("dd", null, String(row[1])));
        });

        return list;
    }

    function buildAgentCard(key, data) {
        var nextAgents = Array.isArray(data.next_agents) ? data.next_agents : [];
        var completed = Array.isArray(data.completed_agents) ? data.completed_agents : [];
        var scheduled = nextAgents.indexOf(key) !== -1;
        var finished = completed.indexOf(key) !== -1;

        var resultMap = {
            reading: data.reading_result,
            qa: data.qa_result,
            research: data.research_result
        };

        var result = resultMap[key] || null;
        var card = el("article", "agent-card" + (scheduled ? "" : " is-idle"));
        var head = el("div", "agent-card-head");

        head.appendChild(el("span", "agent-name", AGENT_META[key].name));
        head.appendChild(el(
            "span",
            "badge-status " + (finished ? "is-done" : "is-idle"),
            finished ? "已完成" : (scheduled ? "未完成" : "未调度")
        ));

        card.appendChild(head);
        card.appendChild(el("p", "agent-desc", AGENT_META[key].desc));

        if (!result) {
            card.appendChild(el("p", "agent-empty", "本轮未返回该 Agent 的结果。"));
            return card;
        }

        var rows = [];

        if (key === "reading") {
            var readingUsage = result.usage || {};
            rows.push(["文本块", result.chunk_count]);
            rows.push(["分批数", result.batch_count]);
            rows.push(["模型", result.model]);
            rows.push(["Token", readingUsage.total_tokens]);
            rows.push(["耗时", typeof result.elapsed_ms === "number" ? result.elapsed_ms + " ms" : null]);

            if (result.report && result.report.overall_summary) {
                var readingDetails = el("details", "citation-details");
                readingDetails.appendChild(el("summary", null, "查看总体总结"));
                readingDetails.appendChild(el("p", null, result.report.overall_summary));
                card.appendChild(buildMetaRows(rows));
                card.appendChild(readingDetails);
                return card;
            }
        }

        if (key === "qa") {
            var retrieval = result.retrieval || {};
            var llm = result.llm || {};
            var llmUsage = llm.usage || {};

            rows.push(["检索模式", retrieval.search_mode]);
            rows.push(["召回条数", retrieval.result_count]);
            rows.push(["引用条数", Array.isArray(result.citations) ? result.citations.length : 0]);
            rows.push(["模型", llm.model]);
            rows.push(["Token", llmUsage.total_tokens]);
            rows.push(["耗时", typeof llm.elapsed_ms === "number" ? llm.elapsed_ms + " ms" : null]);

            card.appendChild(buildMetaRows(rows));

            if (result.answer) {
                var qaDetails = el("details", "citation-details");
                qaDetails.appendChild(el("summary", null, "查看问答回答"));
                qaDetails.appendChild(el("p", null, result.answer));
                card.appendChild(qaDetails);
            }

            return card;
        }

        var researchUsage = result.usage || {};
        var analysis = result.analysis || {};

        rows.push(["证据条数", Array.isArray(result.evidence) ? result.evidence.length : 0]);
        rows.push(["模型", result.model]);
        rows.push(["Token", researchUsage.total_tokens]);
        rows.push(["耗时", typeof result.elapsed_ms === "number" ? result.elapsed_ms + " ms" : null]);

        card.appendChild(buildMetaRows(rows));

        if (analysis.research_problem) {
            var researchDetails = el("details", "citation-details");
            researchDetails.appendChild(el("summary", null, "查看研究问题"));
            researchDetails.appendChild(el("p", null, analysis.research_problem));
            card.appendChild(researchDetails);
        }

        return card;
    }

    function buildRunInfo(data) {
        var card = el("article", "result-card");
        card.appendChild(el("h3", null, "本次执行信息"));

        card.appendChild(buildMetaRows([
            ["请求 ID", data.request_id],
            ["会话 ID", data.thread_id],
            ["原始问题", data.question],
            ["补全后问题", data.resolved_query],
            ["调度 Agent", (data.next_agents || []).join(" → ")],
            ["已完成 Agent", (data.completed_agents || []).join("、")]
        ]));

        if (data.task_plan) {
            card.appendChild(el("p", "result-plan", data.task_plan));
        }

        if (data.error) {
            card.appendChild(el("p", "chat-text", "工作流错误：" + data.error));
        }

        return card;
    }

    function renderResult(data) {
        var host = resultHost();
        var hint = document.getElementById("agentsResultHint");

        host.textContent = "";

        if (hint) {
            hint.textContent = "调度：" + ((data.next_agents || []).join(" → ") || "未调度")
                + " · 完成：" + ((data.completed_agents || []).join("、") || "无");
        }

        host.appendChild(buildPipeline(data));

        var grid = el("div", "agent-grid");
        ["reading", "qa", "research"].forEach(function (key) {
            grid.appendChild(buildAgentCard(key, data));
        });
        host.appendChild(grid);

        if (data.final_answer) {
            var finalCard = el("article", "result-card");
            finalCard.appendChild(el("h3", null, "Supervisor 整合结论"));
            finalCard.appendChild(el("p", "chat-text", data.final_answer));
            host.appendChild(finalCard);
        }

        host.appendChild(buildRunInfo(data));
    }

    function appendHistory(data) {
        state.records.push({
            question: data.question,
            final_answer: data.final_answer,
            request_id: data.request_id,
            thread_id: data.thread_id,
            agents: data.completed_agents || [],
            time: new Date().toISOString()
        });

        var host = document.getElementById("agentsHistory");
        host.textContent = "";

        state.records.slice().reverse().forEach(function (record) {
            var card = el("div", "history-item");
            var details = el("details");
            var summary = el("summary");

            summary.appendChild(el("span", "history-question", record.question || "—"));
            summary.appendChild(el("span", "history-time",
                formatTime(record.time) + " · " + (record.agents.join(" → ") || "未调度")));

            details.appendChild(summary);
            details.appendChild(el("p", "history-answer", record.final_answer || "—"));
            details.appendChild(el("p", "history-meta", "request_id " + (record.request_id || "—")));

            card.appendChild(details);
            host.appendChild(card);
        });
    }

    /* ============================ 提交 ============================ */

    function submitWorkflow(event) {
        event.preventDefault();

        if (state.busy) {
            return;
        }

        var paperId = Number(document.getElementById("agentsPaperSelect").value);
        var question = document.getElementById("agentsQuestion").value.trim();

        if (!paperId) {
            showAlert("请先选择论文。");
            return;
        }

        if (!question) {
            showAlert("请输入问题。");
            return;
        }

        hideAlert();
        setBusy(true);
        updateThreadLabel();
        showNotice(
            "执行中：",
            "工作流正在按 Supervisor 规划执行，耗时取决于调度的 Agent 数量与论文长度，请勿关闭页面…"
        );

        resetResult("工作流执行中，可能持续数分钟至十几分钟，请耐心等待…");

        api().post(
            "/api/agent/ask",
            {
                question: question,
                paper_id: paperId,
                thread_id: state.threadId,
                top_k: 5,
                research_top_k: 8
            },
            { timeout: 1800000 }
        )
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !payload.data) {
                    throw new Error((payload && payload.message) || "工作流返回格式异常");
                }

                hideNotice();
                renderResult(payload.data);
                appendHistory(payload.data);
            })
            .catch(function (error) {
                hideNotice();

                var message = error && error.message ? error.message : "工作流执行失败";

                showAlert(message);

                var host = resultHost();
                host.textContent = "";

                var block = el("div", "empty-state");
                block.appendChild(el("strong", null, "执行失败"));
                block.appendChild(el("span", null, message));
                host.appendChild(block);
            })
            .finally(function () {
                setBusy(false);
            });
    }

    /* ============================ 初始化 ============================ */

    document.addEventListener("DOMContentLoaded", function () {
        if (!window.LitApi) {
            showAlert("请求模块未加载，请检查静态资源是否正常");
            return;
        }

        state.threadId = createThreadId();
        updateThreadLabel();

        document.getElementById("agentsForm").addEventListener("submit", submitWorkflow);

        document.getElementById("agentsPaperSelect").addEventListener("change", function (event) {
            if (state.busy) {
                event.target.value = String(state.paperId || "");
                showAlert("工作流执行中，暂不能切换论文。");
                return;
            }

            state.paperId = Number(event.target.value);
            state.threadId = createThreadId();
            updateThreadLabel();
            resetResult("已切换论文并新建会话，请重新提交问题。");
        });

        document.getElementById("newThreadBtn").addEventListener("click", function () {
            if (state.busy) {
                showAlert("工作流执行中，暂不能新建会话。");
                return;
            }

            state.threadId = createThreadId();
            updateThreadLabel();
            resetResult("已新建会话，此前的执行记录仍保留在页面下方。");
        });

        loadPapers();
    });
})();
