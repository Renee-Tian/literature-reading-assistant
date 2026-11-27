/**
 * 智能阅读页面。
 *
 * - PDF 由 PDF.js 从 /api/papers/<id>/file 加载，仅在浏览器端渲染。
 * - 阅读报告只读取 /api/papers/<id>/reading-report/latest，
 *   不存在时展示空状态，不在前端生成任何内容。
 */
(function () {
    "use strict";

    var scriptElement = document.currentScript;
    var WORKER_SRC = scriptElement
        ? scriptElement.getAttribute("data-worker-src")
        : "";

    var STATUS_MAP = {
        uploaded: { label: "待处理", cls: "is-idle" },
        processing: { label: "处理中", cls: "is-processing" },
        completed: { label: "已完成", cls: "is-done" },
        failed: { label: "处理失败", cls: "is-failed" }
    };

    var REPORT_FIELDS = [
        ["research_background", "研究背景"],
        ["research_problem", "研究问题"],
        ["research_objective", "研究目标"],
        ["research_method", "研究方法"],
        ["experimental_design", "实验设计"],
        ["main_results", "主要结果"],
        ["contributions", "主要贡献"],
        ["limitations", "局限性"],
        ["future_work", "未来工作"],
        ["overall_summary", "总体总结"]
    ];

    var state = {
        paperId: null,
        pdfDoc: null,
        pageNumber: 1,
        scale: 1,
        fitMode: true,
        renderTask: null
    };

    var resizeTimer = null;

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
        var box = document.getElementById("readerAlert");
        var text = document.getElementById("readerAlertText");

        if (!box || !text) {
            return;
        }

        text.textContent = message;
        box.classList.add("is-visible");
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

    /* ============================ 论文信息 ============================ */

    function loadPaper() {
        api().get("/api/papers/" + state.paperId, { timeout: 15000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !payload.data) {
                    throw new Error((payload && payload.message) || "论文信息返回格式异常");
                }

                renderPaper(payload.data);
            })
            .catch(function (error) {
                var message = error && error.message ? error.message : "论文信息加载失败";
                showAlert(message);

                document.getElementById("paperTitle").textContent = "论文不可用";
                document.getElementById("paperSubtitle").textContent = message;

                var meta = document.getElementById("paperMeta");
                meta.textContent = "";
                appendMetaRow(meta, "状态", "—");
            });
    }

    function renderPaper(paper) {
        document.title = (paper.title || "未命名论文") + "｜智能阅读";

        document.getElementById("paperTitle").textContent = paper.title || "未命名论文";
        document.getElementById("paperSubtitle").textContent = [
            paper.authors || null,
            paper.publication_year ? paper.publication_year + " 年" : null,
            paper.original_filename || null
        ].filter(Boolean).join(" · ") || "—";

        document.getElementById("openPdfLink").href = "/api/papers/" + paper.id + "/file";

        var meta = document.getElementById("paperMeta");
        meta.textContent = "";
        appendMetaRow(meta, "状态", statusBadge(paper.status));
        appendMetaRow(meta, "作者", paper.authors || "未填写");
        appendMetaRow(meta, "年份", paper.publication_year || "未填写");
        appendMetaRow(meta, "文件名", paper.original_filename || "—");
        appendMetaRow(meta, "上传时间", formatTime(paper.created_at));

        if (paper.abstract) {
            var details = el("details", "meta-details");
            details.appendChild(el("summary", null, "查看论文摘要"));
            details.appendChild(el("p", null, paper.abstract));
            meta.parentNode.appendChild(details);
        }

        loadStatusDetail();
    }

    function loadStatusDetail() {
        api().get("/api/papers/" + state.paperId + "/status", { timeout: 15000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !payload.data) {
                    return;
                }

                var data = payload.data;

                if (!data.error_message) {
                    return;
                }

                var meta = document.getElementById("paperMeta");
                var errorRow = el("div", "meta-error");
                errorRow.appendChild(el("strong", null, "处理失败原因"));
                errorRow.appendChild(el("span", null, data.error_message));
                meta.parentNode.appendChild(errorRow);
            })
            .catch(function () {
                // 状态详情为辅助信息，失败时不覆盖主信息
            });
    }

    /* ============================ 阅读报告 ============================ */

    function loadReport() {
        api().get(
            "/api/papers/" + state.paperId + "/reading-report/latest",
            { timeout: 20000 }
        )
            .then(function (payload) {
                if (!payload || payload.status !== "success") {
                    throw new Error((payload && payload.message) || "阅读报告返回格式异常");
                }

                renderReport(payload.data);
            })
            .catch(function (error) {
                renderReportError(error && error.message ? error.message : "阅读报告加载失败");
            });
    }

    function renderReportError(message) {
        var host = document.getElementById("reportSection");
        var meta = document.getElementById("reportMeta");

        if (meta) {
            meta.textContent = "阅读报告加载失败";
        }

        if (!host) {
            return;
        }

        host.textContent = "";

        var block = el("div", "empty-state");
        block.appendChild(el("strong", null, "阅读报告加载失败"));
        block.appendChild(el("span", null, message));
        host.appendChild(block);
    }

    function renderReport(report) {
        var host = document.getElementById("reportSection");
        var meta = document.getElementById("reportMeta");

        if (!host) {
            return;
        }

        host.textContent = "";

        if (!report || !report.report_data) {
            if (meta) {
                meta.textContent = "数据库中暂无阅读报告";
            }

            var empty = el("div", "empty-state");
            empty.appendChild(el("strong", null, "暂无阅读报告"));
            empty.appendChild(el("span", null,
                "阅读报告由后端阅读流程生成并写入 reading_reports 表，本页面只读取展示。"));
            host.appendChild(empty);
            return;
        }

        var data = report.report_data;

        if (meta) {
            meta.textContent = "生成于 " + formatTime(report.created_at)
                + " · 模型 " + (report.model_name || "未知");
        }

        REPORT_FIELDS.forEach(function (pair) {
            var value = data[pair[0]];

            if (typeof value !== "string" || !value.trim()) {
                return;
            }

            var field = el("div", "report-field");
            field.appendChild(el("h3", null, pair[1]));
            field.appendChild(el("p", null, value));
            host.appendChild(field);
        });

        if (Array.isArray(data.not_stated) && data.not_stated.length > 0) {
            var block = el("div", "report-field");
            block.appendChild(el("h3", null, "原文未说明"));

            var tags = el("div", "report-tags");

            data.not_stated.forEach(function (item) {
                if (typeof item === "string" && item.trim()) {
                    tags.appendChild(el("span", "report-tag", item));
                }
            });

            block.appendChild(tags);
            host.appendChild(block);
        }
    }

    /* ============================ PDF 渲染 ============================ */

    function pdfOverlay() {
        return document.getElementById("pdfOverlay");
    }

    function hideOverlay() {
        var overlay = pdfOverlay();

        if (overlay) {
            overlay.style.display = "none";
        }
    }

    function showPdfError(message) {
        var overlay = pdfOverlay();

        if (overlay) {
            overlay.className = "pdf-overlay is-error";
            overlay.textContent = message;
            overlay.style.display = "flex";
        }

        showAlert(message);
    }

    function setToolbarEnabled(enabled) {
        ["prevPageBtn", "nextPageBtn", "zoomInBtn", "zoomOutBtn", "fitWidthBtn"].forEach(function (id) {
            var button = document.getElementById(id);

            if (button) {
                button.disabled = !enabled;
            }
        });
    }

    function updateToolbar() {
        var pageInput = document.getElementById("pageInput");
        var prevButton = document.getElementById("prevPageBtn");
        var nextButton = document.getElementById("nextPageBtn");
        var zoomLabel = document.getElementById("zoomLabel");
        var total = state.pdfDoc ? state.pdfDoc.numPages : 0;

        if (pageInput) {
            pageInput.value = String(state.pageNumber);
        }

        if (prevButton) {
            prevButton.disabled = state.pageNumber <= 1;
        }

        if (nextButton) {
            nextButton.disabled = !total || state.pageNumber >= total;
        }

        if (zoomLabel) {
            zoomLabel.textContent = Math.round(state.scale * 100) + "%";
        }
    }

    function applyFitWidth(page) {
        var viewport = page.getViewport({ scale: 1 });
        var container = document.getElementById("pdfViewport");

        if (!container) {
            return;
        }

        var available = Math.max(240, container.clientWidth - 44);
        var scale = available / viewport.width;

        state.scale = Math.min(3, Math.max(0.4, scale));
        state.fitMode = true;
    }

    function renderPage(number) {
        if (!state.pdfDoc) {
            return;
        }

        var canvas = document.getElementById("pdfCanvas");

        if (!canvas) {
            return;
        }

        var context = canvas.getContext("2d");
        var ratio = window.devicePixelRatio || 1;

        state.pdfDoc.getPage(number)
            .then(function (page) {
                var viewport = page.getViewport({ scale: state.scale });

                canvas.width = Math.floor(viewport.width * ratio);
                canvas.height = Math.floor(viewport.height * ratio);
                canvas.style.width = Math.floor(viewport.width) + "px";
                canvas.style.height = Math.floor(viewport.height) + "px";

                if (state.renderTask) {
                    try {
                        state.renderTask.cancel();
                    } catch (error) {
                        // 上一个渲染任务已结束，无需处理
                    }
                }

                state.renderTask = page.render({
                    canvasContext: context,
                    viewport: viewport,
                    transform: ratio !== 1 ? [ratio, 0, 0, ratio, 0, 0] : null
                });

                return state.renderTask.promise.then(function () {
                    state.pageNumber = number;
                    updateToolbar();
                });
            })
            .catch(function (error) {
                if (error && error.name === "RenderingCancelledException") {
                    return;
                }

                showPdfError("页面渲染失败：" + (error && error.message ? error.message : "未知错误"));
            });
    }

    function loadPdf() {
        if (!window.pdfjsLib) {
            showPdfError("PDF.js 未能加载，请检查 static/vendor/pdfjs 目录。");
            return;
        }

        if (WORKER_SRC) {
            window.pdfjsLib.GlobalWorkerOptions.workerSrc = WORKER_SRC;
        }

        window.pdfjsLib.getDocument({
            url: "/api/papers/" + state.paperId + "/file"
        }).promise
            .then(function (doc) {
                state.pdfDoc = doc;

                var pageInput = document.getElementById("pageInput");
                var pageTotal = document.getElementById("pageTotal");

                if (pageInput) {
                    pageInput.max = String(doc.numPages);
                }

                if (pageTotal) {
                    pageTotal.textContent = "/ " + doc.numPages;
                }

                setToolbarEnabled(true);

                return doc.getPage(1).then(function (page) {
                    applyFitWidth(page);
                    hideOverlay();
                    renderPage(1);
                });
            })
            .catch(function (error) {
                setToolbarEnabled(false);
                showPdfError(
                    "PDF 加载失败：" + (error && error.message ? error.message : "未知错误")
                    + "（请确认论文文件存在且后端服务正常）"
                );
            });
    }

    /* ============================ 事件绑定 ============================ */

    function changePage(delta) {
        if (!state.pdfDoc) {
            return;
        }

        var target = state.pageNumber + delta;

        if (target < 1 || target > state.pdfDoc.numPages) {
            return;
        }

        renderPage(target);
    }

    function bindEvents() {
        document.getElementById("prevPageBtn").addEventListener("click", function () {
            changePage(-1);
        });

        document.getElementById("nextPageBtn").addEventListener("click", function () {
            changePage(1);
        });

        document.getElementById("zoomInBtn").addEventListener("click", function () {
            if (!state.pdfDoc) {
                return;
            }

            state.fitMode = false;
            state.scale = Math.min(3, state.scale + 0.15);
            renderPage(state.pageNumber);
        });

        document.getElementById("zoomOutBtn").addEventListener("click", function () {
            if (!state.pdfDoc) {
                return;
            }

            state.fitMode = false;
            state.scale = Math.max(0.4, state.scale - 0.15);
            renderPage(state.pageNumber);
        });

        document.getElementById("fitWidthBtn").addEventListener("click", function () {
            if (!state.pdfDoc) {
                return;
            }

            state.pdfDoc.getPage(state.pageNumber).then(function (page) {
                applyFitWidth(page);
                renderPage(state.pageNumber);
            });
        });

        document.getElementById("pageInput").addEventListener("change", function (event) {
            if (!state.pdfDoc) {
                return;
            }

            var value = Number(event.target.value);

            if (!Number.isInteger(value) || value < 1 || value > state.pdfDoc.numPages) {
                event.target.value = String(state.pageNumber);
                return;
            }

            renderPage(value);
        });

        window.addEventListener("resize", function () {
            if (!state.pdfDoc || !state.fitMode) {
                return;
            }

            window.clearTimeout(resizeTimer);
            resizeTimer = window.setTimeout(function () {
                state.pdfDoc.getPage(state.pageNumber).then(function (page) {
                    applyFitWidth(page);
                    renderPage(state.pageNumber);
                });
            }, 200);
        });
    }

    function readPaperId() {
        var root = document.getElementById("readerRoot");
        var raw = root ? root.getAttribute("data-paper-id") : "";
        var value = Number(raw);

        return Number.isInteger(value) && value > 0 ? value : null;
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!window.LitApi) {
            showAlert("请求模块未加载，请检查静态资源是否正常");
            return;
        }

        state.paperId = readPaperId();

        if (!state.paperId) {
            showAlert("论文 ID 无效，请从论文管理页面进入。");
            showPdfError("论文 ID 无效");
            return;
        }

        bindEvents();
        loadPaper();
        loadReport();
        loadPdf();
    });
})();
