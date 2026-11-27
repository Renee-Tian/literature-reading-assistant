/**
 * 工作台首页：加载真实统计数据、最近论文与服务状态。
 *
 * 所有数字均来自 /api/system/stats、/api/health、/api/db-health，
 * 接口失败时显示错误提示与占位符，不填充任何模拟数据。
 */
(function () {
    "use strict";

    var STATUS_MAP = {
        uploaded: { label: "待处理", cls: "is-idle" },
        processing: { label: "处理中", cls: "is-processing" },
        completed: { label: "已完成", cls: "is-done" },
        failed: { label: "处理失败", cls: "is-failed" }
    };

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

    function getApi() {
        if (!window.LitApi) {
            throw new Error("请求模块未加载");
        }

        return window.LitApi;
    }

    function setStat(key, value) {
        var node = document.querySelector('[data-stat="' + key + '"]');

        if (!node) {
            return;
        }

        if (value === null || value === undefined) {
            node.textContent = "暂未接入";
            node.classList.add("is-muted");
            return;
        }

        node.textContent = Number(value).toLocaleString("zh-CN");
        node.classList.remove("is-muted");
    }

    function showAlert(message) {
        var box = document.getElementById("statsAlert");
        var text = document.getElementById("statsAlertText");

        if (!box || !text) {
            return;
        }

        text.textContent = message;
        box.classList.add("is-visible");
    }

    function hideAlert() {
        var box = document.getElementById("statsAlert");

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

    function renderRecentPapers(papers) {
        var host = document.getElementById("recentPapers");

        if (!host) {
            return;
        }

        host.textContent = "";

        if (!Array.isArray(papers) || papers.length === 0) {
            var empty = el("div", "empty-state");
            empty.appendChild(el("strong", null, "还没有上传论文"));
            empty.appendChild(el("span", null, "前往论文管理上传 PDF 后，这里会显示最近记录。"));
            host.appendChild(empty);
            return;
        }

        var table = el("table", "data-table");
        var thead = el("thead");
        var headRow = el("tr");
        ["论文", "状态", "年份", "上传时间", "操作"].forEach(function (label) {
            headRow.appendChild(el("th", null, label));
        });
        thead.appendChild(headRow);

        var tbody = el("tbody");

        papers.forEach(function (paper) {
            var row = el("tr");

            var titleCell = el("td");
            titleCell.appendChild(el("span", "cell-title", paper.title || "未命名论文"));
            titleCell.appendChild(el("span", "cell-sub", paper.original_filename || "—"));
            row.appendChild(titleCell);

            var statusCell = el("td");
            statusCell.appendChild(statusBadge(paper.status));
            row.appendChild(statusCell);

            row.appendChild(el("td", null, paper.publication_year || "—"));
            row.appendChild(el("td", null, formatTime(paper.created_at)));

            var actionCell = el("td");
            var actions = el("div", "cell-actions");

            var readerLink = el("a", "link-quiet", "阅读");
            readerLink.href = "/papers/" + paper.id + "/reader";

            var chatLink = el("a", "link-quiet", "问答");
            chatLink.href = "/chat?paper_id=" + paper.id;

            actions.appendChild(readerLink);
            actions.appendChild(chatLink);
            actionCell.appendChild(actions);
            row.appendChild(actionCell);

            tbody.appendChild(row);
        });

        table.appendChild(thead);
        table.appendChild(tbody);
        host.appendChild(table);
    }

    function renderServiceList(items) {
        var host = document.getElementById("serviceStatus");

        if (!host) {
            return;
        }

        host.textContent = "";

        items.forEach(function (item) {
            var row = el("li");
            row.appendChild(el("span", "status-name", item.name));

            var value = el("span", "status-value", item.value);

            if (item.state === "error") {
                value.style.color = "var(--color-danger)";
            }

            row.appendChild(value);
            host.appendChild(row);
        });
    }

    function loadStats() {
        var api = getApi();

        return api.get("/api/system/stats", { timeout: 20000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !payload.data) {
                    throw new Error((payload && payload.message) || "统计接口返回格式异常");
                }

                var data = payload.data;
                var status = data.paper_status || {};

                hideAlert();
                setStat("paper_total", data.paper_total || 0);
                setStat("paper_completed", status.completed || 0);
                setStat("paper_uploaded", status.uploaded || 0);
                setStat("paper_failed", status.failed || 0);
                setStat("chunk_total", data.chunk_total || 0);
                setStat("vector_total", data.vector_total === null ? null : data.vector_total || 0);
                setStat("qa_record_total", data.qa_record_total || 0);
                setStat("reading_report_total", data.reading_report_total || 0);

                renderRecentPapers(data.recent_papers);

                if (data.vector_error) {
                    showAlert("向量库统计不可用：" + data.vector_error + "（其余统计正常）");
                }
            })
            .catch(function (error) {
                ["paper_total", "paper_completed", "paper_uploaded", "paper_failed",
                    "chunk_total", "vector_total", "qa_record_total", "reading_report_total"
                ].forEach(function (key) {
                    var node = document.querySelector('[data-stat="' + key + '"]');

                    if (node) {
                        node.textContent = "—";
                        node.classList.add("is-muted");
                    }
                });

                renderRecentPapers([]);
                showAlert(error && error.message ? error.message : "统计接口请求失败");
            });
    }

    function loadServices() {
        var api = getApi();

        var health = api.get("/api/health", { timeout: 8000 })
            .then(function (payload) {
                return {
                    name: "Flask 后端",
                    value: payload && payload.status === "ok" ? "运行正常" : "返回异常状态",
                    state: payload && payload.status === "ok" ? "ok" : "error"
                };
            })
            .catch(function (error) {
                return {
                    name: "Flask 后端",
                    value: error && error.message ? error.message : "不可用",
                    state: "error"
                };
            });

        var database = api.get("/api/db-health", { timeout: 8000 })
            .then(function (payload) {
                return {
                    name: "MySQL 数据库",
                    value: payload && payload.status === "ok"
                        ? "连接正常" + (payload.database ? "（" + payload.database + "）" : "")
                        : "返回异常状态",
                    state: payload && payload.status === "ok" ? "ok" : "error"
                };
            })
            .catch(function (error) {
                return {
                    name: "MySQL 数据库",
                    value: error && error.message ? error.message : "连接失败",
                    state: "error"
                };
            });

        return Promise.all([health, database]).then(renderServiceList);
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!window.LitApi) {
            showAlert("请求模块未加载，请检查静态资源是否正常");
            return;
        }

        loadStats();
        loadServices();
    });
})();
