/**
 * 研究分析页面。
 *
 * 唯一数据入口：POST /api/agent/ask
 * 页面只渲染 Supervisor 与 Research Agent 的真实返回结果。
 */
(function () {
    "use strict";

    var RECOMMENDED_TASK = "请分析这篇论文的研究问题、研究方法与技术路线、涉及的算法或模型、"
        + "实验设计、使用的数据集、评价指标、主要实验结果、论文贡献与局限性。";

    var STRING_FIELDS = [
        ["research_problem", "研究问题"],
        ["methodology", "研究方法"],
        ["experimental_design", "实验设计"],
        ["results", "主要结果"]
    ];

    var LIST_FIELDS = [
        ["algorithms", "算法 / 模型"],
        ["datasets", "数据集"],
        ["metrics", "评价指标"],
        ["contributions", "主要贡献"],
        ["limitations", "局限性"]
    ];

    var state = {
        papers: [],
        paperId: null,
        busy: false
    };

    var noticeTimer = null;

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
        var box = document.getElementById("researchAlert");
        var text = document.getElementById("researchAlertText");

        if (box && text) {
            text.textContent = message;
            box.classList.add("is-visible");
        }
    }

    function hideAlert() {
        var box = document.getElementById("researchAlert");

        if (box) {
            box.classList.remove("is-visible");
        }
    }

    function showNotice(title, text) {
        var box = document.getElementById("researchNotice");
        var titleNode = document.getElementById("researchNoticeTitle");
        var textNode = document.getElementById("researchNoticeText");

        if (!box || !titleNode || !textNode) {
            return;
        }

        window.clearTimeout(noticeTimer);
        titleNode.textContent = title;
        textNode.textContent = text;
        box.classList.add("is-visible");
    }

    function hideNotice() {
        var box = document.getElementById("researchNotice");

        if (box) {
            box.classList.remove("is-visible");
        }
    }

    function setBusy(busy) {
        state.busy = busy;

        var button = document.getElementById("researchSubmitBtn");

        if (button) {
            button.disabled = busy;
            button.textContent = busy ? "执行中…" : "开始分析";
        }
    }

    /* ============================ 论文加载 ============================ */

    function loadPapers() {
        var select = document.getElementById("researchPaperSelect");

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
        return document.getElementById("researchResult");
    }

    function resetResultHost() {
        var host = resultHost();
        host.textContent = "";
        return host;
    }

    function buildCard(title) {
        var card = el("article", "result-card");
        card.appendChild(el("h3", null, title));
        return card;
    }

    function appendField(parent, label, text) {
        var field = el("div", "report-field");
        field.appendChild(el("h3", null, label));
        field.appendChild(el("p", null, text));
        parent.appendChild(field);
    }

    function appendTags(parent, label, items) {
        var valid = (items || []).filter(function (item) {
            return typeof item === "string" && item.trim();
        });

        if (valid.length === 0) {
            return;
        }

        var field = el("div", "report-field");
        field.appendChild(el("h3", null, label));

        var tags = el("div", "report-tags");

        valid.forEach(function (item) {
            tags.appendChild(el("span", "report-tag", item));
        });

        field.appendChild(tags);
        parent.appendChild(field);
    }

    function buildEvidenceCard(item, index) {
        var card = el("article", "citation-card");
        var head = el("div", "citation-head");

        head.appendChild(el("span", "citation-id", item.evidence_id || "E" + (index + 1)));
        head.appendChild(el("span", "citation-page",
            item.page_number ? "第 " + item.page_number + " 页" : "页码未知"));

        if (typeof item.chunk_index === "number") {
            head.appendChild(el("span", "citation-chunk", "Chunk " + item.chunk_index));
        }

        card.appendChild(head);

        var metaParts = [];

        if (typeof item.rrf_score === "number") {
            metaParts.push("RRF " + item.rrf_score.toFixed(4));
        }

        if (typeof item.dense_rank === "number") {
            metaParts.push("Dense #" + item.dense_rank);
        }

        if (typeof item.sparse_rank === "number") {
            metaParts.push("Sparse #" + item.sparse_rank);
        }

        if (Array.isArray(item.retrieval_sources) && item.retrieval_sources.length > 0) {
            metaParts.push("来源 " + item.retrieval_sources.join("、"));
        }

        if (metaParts.length > 0) {
            card.appendChild(el("p", "citation-meta", metaParts.join(" · ")));
        }

        if (item.content) {
            var details = el("details", "citation-details");
            details.appendChild(el("summary", null, "查看原文片段"));
            details.appendChild(el("p", null, item.content));
            card.appendChild(details);
        }

        return card;
    }

    function renderResult(data) {
        var host = resetResultHost();
        var hint = document.getElementById("researchResultHint");
        var nextAgents = Array.isArray(data.next_agents) ? data.next_agents : [];
        var completed = Array.isArray(data.completed_agents) ? data.completed_agents : [];
        var researchResult = data.research_result || null;

        if (hint) {
            hint.textContent = "调度：" + (nextAgents.length ? nextAgents.join(" → ") : "未调度专业 Agent")
                + " · 完成：" + (completed.length ? completed.join("、") : "无");
        }

        /* 1. Supervisor 规划 */
        var planningCard = buildCard("Supervisor 任务规划");

        var meta = el("dl", "meta-list");
        [
            ["请求 ID", data.request_id || "—"],
            ["会话 ID", data.thread_id || "—"],
            ["补全后问题", data.resolved_query || data.question || "—"],
            ["调度 Agent", nextAgents.length ? nextAgents.join(" → ") : "未调度"],
            ["已完成", completed.length ? completed.join("、") : "无"]
        ].forEach(function (pair) {
            meta.appendChild(el("dt", null, pair[0]));
            meta.appendChild(el("dd", null, pair[1]));
        });

        planningCard.appendChild(meta);

        if (data.task_plan) {
            planningCard.appendChild(el("p", "result-plan", data.task_plan));
        }

        host.appendChild(planningCard);

        /* 2. Research Agent 分析 */
        if (researchResult && researchResult.analysis) {
            var analysis = researchResult.analysis;
            var analysisCard = buildCard("Research Agent 分析");

            STRING_FIELDS.forEach(function (pair) {
                var value = analysis[pair[0]];

                if (typeof value === "string" && value.trim()) {
                    appendField(analysisCard, pair[1], value);
                }
            });

            LIST_FIELDS.forEach(function (pair) {
                appendTags(analysisCard, pair[1], analysis[pair[0]]);
            });

            if (Array.isArray(analysis.evidence_ids) && analysis.evidence_ids.length > 0) {
                appendTags(analysisCard, "引用证据编号", analysis.evidence_ids);
            }

            var usage = researchResult.usage || {};
            var infoParts = [];

            if (researchResult.model) {
                infoParts.push("模型 " + researchResult.model);
            }

            if (typeof usage.total_tokens === "number") {
                infoParts.push("Token " + usage.total_tokens);
            }

            if (typeof researchResult.elapsed_ms === "number") {
                infoParts.push("耗时 " + researchResult.elapsed_ms + " ms");
            }

            if (infoParts.length > 0) {
                analysisCard.appendChild(el("p", "chat-info", infoParts.join(" · ")));
            }

            host.appendChild(analysisCard);

            var evidence = Array.isArray(researchResult.evidence) ? researchResult.evidence : [];
            var evidenceCard = buildCard("原文证据 · " + evidence.length + " 条");

            if (evidence.length === 0) {
                evidenceCard.appendChild(el("p", "citation-empty", "本轮没有返回可用证据。"));
            } else {
                var list = el("div", "citation-list");

                evidence.forEach(function (item, index) {
                    list.appendChild(buildEvidenceCard(item, index));
                });

                evidenceCard.appendChild(list);
            }

            host.appendChild(evidenceCard);
        } else {
            var skipCard = buildCard("Research Agent 未执行");
            skipCard.appendChild(el(
                "p",
                "result-plan",
                "本轮 Supervisor 没有调度 Research Agent，因此没有研究分析结果。"
                + "可参考下方整合结论，或将任务描述改为明确的研究分析要求后重试。"
            ));
            host.appendChild(skipCard);
        }

        /* 3. 最终整合结论 */
        if (data.final_answer) {
            var finalCard = buildCard("Supervisor 整合结论");
            finalCard.appendChild(el("p", "chat-text", data.final_answer));
            host.appendChild(finalCard);
        }

        if (data.error) {
            var errorCard = buildCard("工作流返回的错误信息");
            errorCard.appendChild(el("p", "chat-text", data.error));
            host.appendChild(errorCard);
        }
    }

    function renderError(message) {
        var host = resetResultHost();
        var hint = document.getElementById("researchResultHint");

        if (hint) {
            hint.textContent = "执行失败";
        }

        var block = el("div", "empty-state");
        block.appendChild(el("strong", null, "分析请求失败"));
        block.appendChild(el("span", null, message));
        host.appendChild(block);
    }

    /* ============================ 提交任务 ============================ */

    function submitTask(event) {
        event.preventDefault();

        if (state.busy) {
            return;
        }

        var paperSelect = document.getElementById("researchPaperSelect");
        var questionInput = document.getElementById("researchQuestion");
        var paperId = Number(paperSelect.value);
        var question = questionInput.value.trim();

        if (!paperId) {
            showAlert("请先选择论文。");
            return;
        }

        if (!question) {
            showAlert("请填写分析任务。");
            return;
        }

        var topK = Number(document.getElementById("researchTopK").value) || 8;

        hideAlert();
        setBusy(true);
        showNotice(
            "执行中：",
            "Supervisor 正在规划并调度 Agent，耗时取决于任务复杂度与论文长度，请勿关闭页面…"
        );

        var host = resetResultHost();
        host.appendChild(el(
            "div",
            "empty-state",
            "工作流执行中，通常需要数分钟，请耐心等待…"
        ));

        api().post(
            "/api/agent/ask",
            {
                question: question,
                paper_id: paperId,
                top_k: topK,
                research_top_k: topK
            },
            { timeout: 1200000 }
        )
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !payload.data) {
                    throw new Error((payload && payload.message) || "工作流返回格式异常");
                }

                hideNotice();
                renderResult(payload.data);
            })
            .catch(function (error) {
                hideNotice();
                var message = error && error.message ? error.message : "工作流执行失败";
                renderError(message);
                showAlert(message);
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

        document.getElementById("researchForm").addEventListener("submit", submitTask);

        document.getElementById("fillTemplateBtn").addEventListener("click", function () {
            document.getElementById("researchQuestion").value = RECOMMENDED_TASK;
        });

        document.getElementById("researchPaperSelect").addEventListener("change", function (event) {
            state.paperId = Number(event.target.value);
        });

        loadPapers();
    });
})();
