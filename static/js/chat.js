/**
 * 智能问答页面（单轮检索问答）。
 *
 * 数据来源：
 * - GET  /api/papers/?limit=100
 * - GET  /api/papers/<id>
 * - POST /api/papers/<id>/qa
 * - GET  /api/papers/<id>/qa/history?limit=20
 *
 * 页面只渲染后端返回的 answer / citations / retrieval / llm，
 * 不在前端做任何检索或推断。
 */
(function () {
    "use strict";

    var STATUS_MAP = {
        uploaded: { label: "待处理", cls: "is-idle" },
        processing: { label: "处理中", cls: "is-processing" },
        completed: { label: "已完成", cls: "is-done" },
        failed: { label: "处理失败", cls: "is-failed" }
    };

    var state = {
        papers: [],
        paperId: null,
        busy: false
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
        var box = document.getElementById("chatAlert");
        var text = document.getElementById("chatAlertText");

        if (!box || !text) {
            return;
        }

        text.textContent = message;
        box.classList.add("is-visible");
    }

    function hideAlert() {
        var box = document.getElementById("chatAlert");

        if (box) {
            box.classList.remove("is-visible");
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

    function statusBadge(status) {
        var config = STATUS_MAP[status] || { label: status || "未知", cls: "" };
        return el("span", "badge-status" + (config.cls ? " " + config.cls : ""), config.label);
    }

    function appendMetaRow(list, label, value) {
        var term = el("dt", null, label);
        var desc = el("dd");

        if (value instanceof Node) {
            desc.appendChild(value);
        } else {
            desc.textContent = value === null || value === undefined || value === ""
                ? "—"
                : String(value);
        }

        list.appendChild(term);
        list.appendChild(desc);
    }

    function stream() {
        return document.getElementById("chatStream");
    }

    function scrollToBottom() {
        var host = stream();

        if (host) {
            host.scrollTop = host.scrollHeight;
        }
    }

    /* ============================ 论文选择 ============================ */

    function loadPapers() {
        api().get("/api/papers/?limit=100", { timeout: 20000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !Array.isArray(payload.data)) {
                    throw new Error((payload && payload.message) || "论文列表返回格式异常");
                }

                state.papers = payload.data;
                buildPaperSelect();
            })
            .catch(function (error) {
                var select = document.getElementById("paperSelect");
                select.textContent = "";
                select.appendChild(el("option", null, "论文列表加载失败"));
                showAlert(error && error.message ? error.message : "论文列表加载失败");
            });
    }

    function buildPaperSelect() {
        var select = document.getElementById("paperSelect");
        var hint = document.getElementById("paperHint");

        select.textContent = "";

        if (state.papers.length === 0) {
            select.appendChild(el("option", null, "还没有论文"));
            select.disabled = true;

            if (hint) {
                hint.textContent = "请先在论文管理上传 PDF";
            }

            document.getElementById("askBtn").disabled = true;
            return;
        }

        state.papers.forEach(function (paper) {
            var option = el("option", null, paper.title + "（#" + paper.id + "）");
            option.value = String(paper.id);
            select.appendChild(option);
        });

        var requested = Number(new URLSearchParams(window.location.search).get("paper_id"));
        var matched = state.papers.filter(function (paper) {
            return paper.id === requested;
        })[0];

        var targetId = matched ? matched.id : state.papers[0].id;
        select.value = String(targetId);
        selectPaper(targetId);
    }

    function selectPaper(paperId) {
        if (!paperId || state.paperId === paperId) {
            return;
        }

        state.paperId = paperId;
        clearChat();
        loadPaperDetail(paperId);
        loadHistory(paperId);
    }

    function loadPaperDetail(paperId) {
        api().get("/api/papers/" + paperId, { timeout: 15000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !payload.data) {
                    throw new Error((payload && payload.message) || "论文信息返回格式异常");
                }

                renderSideMeta(payload.data);
            })
            .catch(function (error) {
                showAlert(error && error.message ? error.message : "论文信息加载失败");
            });
    }

    function renderSideMeta(paper) {
        var meta = document.getElementById("sideMeta");
        var sideHint = document.getElementById("sideHint");
        var paperHint = document.getElementById("paperHint");

        meta.textContent = "";
        appendMetaRow(meta, "标题", paper.title || "—");
        appendMetaRow(meta, "状态", statusBadge(paper.status));
        appendMetaRow(meta, "作者", paper.authors || "未填写");
        appendMetaRow(meta, "年份", paper.publication_year || "未填写");
        appendMetaRow(meta, "文件名", paper.original_filename || "—");

        if (sideHint) {
            sideHint.textContent = paper.title || "—";
        }

        if (paperHint) {
            if (paper.status === "completed") {
                paperHint.textContent = "已完成解析，可进行检索问答";
            } else if (paper.status === "failed") {
                paperHint.textContent = "解析失败，建议先在论文管理重新解析";
            } else {
                paperHint.textContent = "尚未完成解析，问答可能缺少原文证据";
            }
        }
    }

    /* ============================ 历史记录 ============================ */

    function loadHistory(paperId) {
        var host = document.getElementById("historyList");

        host.textContent = "";
        host.appendChild(el("div", "empty-state", "正在加载…"));

        api().get(
            "/api/papers/" + paperId + "/qa/history?limit=20",
            { timeout: 20000 }
        )
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !payload.data) {
                    throw new Error((payload && payload.message) || "历史记录返回格式异常");
                }

                renderHistory(payload.data.items || []);
            })
            .catch(function (error) {
                host.textContent = "";
                host.appendChild(el(
                    "div",
                    "empty-state",
                    error && error.message ? error.message : "历史记录加载失败"
                ));
            });
    }

    function renderHistory(items) {
        var host = document.getElementById("historyList");

        host.textContent = "";

        if (!Array.isArray(items) || items.length === 0) {
            host.appendChild(el("div", "empty-state", "暂无历史问答"));
            return;
        }

        items.forEach(function (item) {
            var card = el("div", "history-item");
            var details = el("details");
            var summary = el("summary");

            summary.appendChild(el("span", "history-question", item.question || "（无问题）"));
            summary.appendChild(el("span", "history-time", formatTime(item.created_at)));

            details.appendChild(summary);
            details.appendChild(el("p", "history-answer", item.answer || "—"));

            var count = Array.isArray(item.citations) ? item.citations.length : 0;
            details.appendChild(el("p", "history-meta", "引用 " + count + " 条"));

            card.appendChild(details);
            host.appendChild(card);
        });
    }

    /* ============================ 对话渲染 ============================ */

    function clearChat() {
        var host = stream();

        if (!host) {
            return;
        }

        host.textContent = "";

        var empty = el("div", "empty-state");
        empty.appendChild(el("strong", null, "开始提问"));
        empty.appendChild(el("span", null, "选择论文后提问，回答会附带原文证据编号与页码。"));
        host.appendChild(empty);
    }

    function appendUserMessage(text) {
        var host = stream();
        var wrap = el("div", "chat-message is-user");
        var bubble = el("div", "chat-bubble");

        bubble.appendChild(el("p", "chat-text", text));
        wrap.appendChild(bubble);
        wrap.appendChild(el("span", "chat-avatar", "我"));
        host.appendChild(wrap);
        scrollToBottom();
    }

    function appendLoading() {
        var host = stream();
        var wrap = el("div", "chat-message is-assistant");
        var bubble = el("div", "chat-bubble");

        wrap.id = "qaLoading";
        bubble.appendChild(el("span", "chat-typing",
            "正在检索原文并生成回答（通常需要 1–3 分钟），请勿关闭页面…"));
        wrap.appendChild(el("span", "chat-avatar", "AI"));
        wrap.appendChild(bubble);
        host.appendChild(wrap);
        scrollToBottom();

        return wrap;
    }

    function removeLoading(node) {
        if (node && node.parentNode) {
            node.parentNode.removeChild(node);
        }
    }

    function appendError(message) {
        var host = stream();
        var wrap = el("div", "chat-message is-assistant");
        var bubble = el("div", "chat-bubble is-error");

        bubble.appendChild(el("p", "chat-text", "请求失败：" + message));
        wrap.appendChild(el("span", "chat-avatar", "AI"));
        wrap.appendChild(bubble);
        host.appendChild(wrap);
        scrollToBottom();
    }

    function buildCitationCard(citation, index) {
        var card = el("article", "citation-card");
        var head = el("div", "citation-head");

        head.appendChild(el(
            "span",
            "citation-id",
            citation.evidence_id || "E" + (index + 1)
        ));

        head.appendChild(el(
            "span",
            "citation-page",
            citation.page_number ? "第 " + citation.page_number + " 页" : "页码未知"
        ));

        if (typeof citation.chunk_index === "number") {
            head.appendChild(el("span", "citation-chunk", "Chunk " + citation.chunk_index));
        }

        card.appendChild(head);

        if (citation.quote) {
            card.appendChild(el("blockquote", "citation-quote", citation.quote));
        }

        if (citation.reason) {
            card.appendChild(el("p", "citation-reason", "依据：" + citation.reason));
        }

        var metaParts = [];

        if (typeof citation.rrf_score === "number") {
            metaParts.push("RRF " + citation.rrf_score.toFixed(4));
        }

        if (typeof citation.dense_rank === "number") {
            metaParts.push("Dense #" + citation.dense_rank);
        }

        if (typeof citation.sparse_rank === "number") {
            metaParts.push("Sparse #" + citation.sparse_rank);
        }

        if (Array.isArray(citation.retrieval_sources) && citation.retrieval_sources.length > 0) {
            metaParts.push("来源 " + citation.retrieval_sources.join("、"));
        }

        if (metaParts.length > 0) {
            card.appendChild(el("p", "citation-meta", metaParts.join(" · ")));
        }

        if (citation.content) {
            var details = el("details", "citation-details");
            details.appendChild(el("summary", null, "查看完整原文片段"));
            details.appendChild(el("p", null, citation.content));
            card.appendChild(details);
        }

        return card;
    }

    function buildInfoLine(retrieval, llm) {
        var parts = [];

        if (retrieval) {
            if (retrieval.search_mode) {
                parts.push("检索模式 " + retrieval.search_mode);
            }

            if (typeof retrieval.result_count === "number") {
                parts.push("召回 " + retrieval.result_count + " 条");
            }

            if (retrieval.embedding_model) {
                parts.push("向量模型 " + retrieval.embedding_model);
            }

            if (typeof retrieval.embedding_time_ms === "number") {
                parts.push("向量耗时 " + retrieval.embedding_time_ms + " ms");
            }
        }

        if (llm) {
            if (llm.model) {
                parts.push("生成模型 " + llm.model);
            }

            if (llm.usage && typeof llm.usage.total_tokens === "number") {
                parts.push("Token " + llm.usage.total_tokens);
            }

            if (typeof llm.elapsed_ms === "number") {
                parts.push("生成耗时 " + llm.elapsed_ms + " ms");
            }
        }

        return parts.join(" · ");
    }

    function appendAssistantMessage(data) {
        var host = stream();
        var wrap = el("div", "chat-message is-assistant");
        var bubble = el("div", "chat-bubble");

        bubble.appendChild(el("p", "chat-text", data.answer || "（回答内容为空）"));

        var citations = Array.isArray(data.citations) ? data.citations : [];
        var citationBlock = el("div", "citation-block");

        citationBlock.appendChild(el(
            "p",
            "citation-title",
            citations.length > 0
                ? "引用证据 · " + citations.length + " 条"
                : "引用证据 · 本次未返回"
        ));

        if (citations.length > 0) {
            var list = el("div", "citation-list");

            citations.forEach(function (citation, index) {
                list.appendChild(buildCitationCard(citation, index));
            });

            citationBlock.appendChild(list);
        } else {
            citationBlock.appendChild(el(
                "p",
                "citation-empty",
                "本轮回答没有可展示的引用证据，请确认论文已完成解析与向量入库。"
            ));
        }

        bubble.appendChild(citationBlock);

        var info = buildInfoLine(data.retrieval, data.llm);

        if (info) {
            bubble.appendChild(el("p", "chat-info", info));
        }

        wrap.appendChild(el("span", "chat-avatar", "AI"));
        wrap.appendChild(bubble);
        host.appendChild(wrap);
        scrollToBottom();
    }

    /* ============================ 提问 ============================ */

    function setBusy(busy) {
        state.busy = busy;

        var button = document.getElementById("askBtn");

        if (button) {
            button.disabled = busy;
            button.textContent = busy ? "生成中…" : "发送";
        }
    }

    function submitQuestion(event) {
        event.preventDefault();

        if (state.busy) {
            return;
        }

        var input = document.getElementById("questionInput");
        var question = input.value.trim();

        if (!question) {
            showAlert("请输入问题。");
            return;
        }

        if (!state.paperId) {
            showAlert("请先选择论文。");
            return;
        }

        var topK = Number(document.getElementById("topKSelect").value) || 5;

        hideAlert();
        appendUserMessage(question);
        input.value = "";

        var loading = appendLoading();
        setBusy(true);

        api().post(
            "/api/papers/" + state.paperId + "/qa",
            {
                question: question,
                top_k: topK,
                save_history: true
            },
            { timeout: 480000 }
        )
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !payload.data) {
                    throw new Error((payload && payload.message) || "问答失败");
                }

                removeLoading(loading);
                appendAssistantMessage(payload.data);
                loadHistory(state.paperId);
            })
            .catch(function (error) {
                removeLoading(loading);
                appendError(error && error.message ? error.message : "问答请求失败");
                input.value = question;
            })
            .finally(function () {
                setBusy(false);
            });
    }

    /* ============================ 事件绑定 ============================ */

    function bindEvents() {
        document.getElementById("qaForm").addEventListener("submit", submitQuestion);

        document.getElementById("questionInput").addEventListener("keydown", function (event) {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                document.getElementById("qaForm").requestSubmit();
            }
        });

        document.getElementById("paperSelect").addEventListener("change", function (event) {
            if (state.busy) {
                event.target.value = String(state.paperId || "");
                showAlert("当前问答尚未完成，请稍后再切换论文。");
                return;
            }

            selectPaper(Number(event.target.value));
        });

        document.getElementById("clearChatBtn").addEventListener("click", function () {
            if (state.busy) {
                showAlert("当前问答尚未完成，请稍后再清空。");
                return;
            }

            clearChat();
            hideAlert();
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!window.LitApi) {
            showAlert("请求模块未加载，请检查静态资源是否正常");
            return;
        }

        bindEvents();
        loadPapers();
    });
})();
