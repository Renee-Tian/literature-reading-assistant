/**
 * 论文管理页面。
 *
 * 数据来源：
 * - GET  /api/papers/?limit=100
 * - POST /api/papers/upload
 * - PATCH /api/papers/<id>
 * - DELETE /api/papers/<id>
 * - POST /api/papers/<id>/process
 * - POST /api/papers/<id>/index
 */
(function () {
    "use strict";

    var MAX_FILE_SIZE = 30 * 1024 * 1024;

    var STATUS_MAP = {
        uploaded: { label: "待处理", cls: "is-idle" },
        processing: { label: "处理中", cls: "is-processing" },
        completed: { label: "已完成", cls: "is-done" },
        failed: { label: "处理失败", cls: "is-failed" }
    };

    var state = {
        papers: [],
        keyword: "",
        status: "all",
        selectedFile: null,
        busy: false,
        editingId: null
    };

    var editModal = null;
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
        var box = document.getElementById("pageAlert");
        var text = document.getElementById("pageAlertText");

        if (!box || !text) {
            return;
        }

        text.textContent = message;
        box.classList.add("is-visible");
    }

    function hideAlert() {
        var box = document.getElementById("pageAlert");

        if (box) {
            box.classList.remove("is-visible");
        }
    }

    function hideNotice() {
        var box = document.getElementById("opNotice");

        if (box) {
            box.classList.remove("is-visible");
        }
    }

    function showNotice(title, text, autoHide) {
        var box = document.getElementById("opNotice");
        var titleNode = document.getElementById("opNoticeTitle");
        var textNode = document.getElementById("opNoticeText");

        if (!box || !titleNode || !textNode) {
            return;
        }

        titleNode.textContent = title;
        textNode.textContent = text;
        box.classList.add("is-visible");

        window.clearTimeout(noticeTimer);

        if (autoHide) {
            noticeTimer = window.setTimeout(hideNotice, 8000);
        }
    }

    function setBusy(busy) {
        state.busy = busy;

        var uploadBtn = document.getElementById("uploadBtn");
        var refreshBtn = document.getElementById("refreshBtn");

        if (uploadBtn) {
            uploadBtn.disabled = busy;
            uploadBtn.textContent = busy ? "处理中…" : "开始上传";
        }

        if (refreshBtn) {
            refreshBtn.disabled = busy;
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

    function formatSize(bytes) {
        if (bytes >= 1024 * 1024) {
            return (bytes / (1024 * 1024)).toFixed(1) + " MiB";
        }

        return Math.max(1, Math.round(bytes / 1024)) + " KiB";
    }

    function statusBadge(status) {
        var config = STATUS_MAP[status] || { label: status || "未知", cls: "" };
        return el("span", "badge-status" + (config.cls ? " " + config.cls : ""), config.label);
    }

    /* ============================ 列表加载与渲染 ============================ */

    function tableHost() {
        return document.getElementById("papersTableWrap");
    }

    function renderLoading() {
        var host = tableHost();

        if (!host) {
            return;
        }

        host.textContent = "";
        host.appendChild(el("div", "empty-state", "正在加载论文列表…"));
    }

    function renderLoadError(message) {
        var host = tableHost();

        if (!host) {
            return;
        }

        host.textContent = "";

        var block = el("div", "empty-state");
        block.appendChild(el("strong", null, "论文列表加载失败"));
        block.appendChild(el("span", null, message || "请检查后端服务"));
        host.appendChild(block);
    }

    function filteredPapers() {
        var keyword = state.keyword.trim().toLowerCase();

        return state.papers.filter(function (paper) {
            if (state.status !== "all" && paper.status !== state.status) {
                return false;
            }

            if (!keyword) {
                return true;
            }

            var haystack = [
                paper.title,
                paper.original_filename,
                paper.authors
            ].filter(Boolean).join(" ").toLowerCase();

            return haystack.indexOf(keyword) !== -1;
        });
    }

    function updateSummary(visibleCount) {
        var node = document.getElementById("listSummary");

        if (!node) {
            return;
        }

        node.textContent = "共 " + state.papers.length + " 篇，当前显示 " + visibleCount + " 篇";
    }

    function buildActionCell(paper) {
        var cell = el("td");
        var actions = el("div", "cell-actions");

        var readerLink = el("a", "link-quiet", "阅读");
        readerLink.href = "/papers/" + paper.id + "/reader";

        var chatLink = el("a", "link-quiet", "问答");
        chatLink.href = "/chat?paper_id=" + paper.id;

        var dropdown = el("div", "dropdown");
        var toggle = el("button", "btn-icon", "•••");
        toggle.type = "button";
        toggle.setAttribute("data-bs-toggle", "dropdown");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "更多操作");

        var menu = el("ul", "dropdown-menu dropdown-menu-end");

        [
            { action: "process", label: "解析 PDF" },
            { action: "index", label: "向量入库" },
            { action: "edit", label: "编辑信息" }
        ].forEach(function (item) {
            var li = el("li");
            var button = el("button", "dropdown-item", item.label);
            button.type = "button";
            button.setAttribute("data-action", item.action);
            button.setAttribute("data-id", String(paper.id));
            li.appendChild(button);
            menu.appendChild(li);
        });

        menu.appendChild(el("li"));
        menu.lastChild.appendChild(el("hr", "dropdown-divider"));

        var deleteItem = el("li");
        var deleteButton = el("button", "dropdown-item text-danger", "删除论文");
        deleteButton.type = "button";
        deleteButton.setAttribute("data-action", "delete");
        deleteButton.setAttribute("data-id", String(paper.id));
        deleteItem.appendChild(deleteButton);
        menu.appendChild(deleteItem);

        dropdown.appendChild(toggle);
        dropdown.appendChild(menu);

        actions.appendChild(readerLink);
        actions.appendChild(chatLink);
        actions.appendChild(dropdown);
        cell.appendChild(actions);

        return cell;
    }

    function renderTable() {
        var host = tableHost();

        if (!host) {
            return;
        }

        var papers = filteredPapers();
        updateSummary(papers.length);
        host.textContent = "";

        if (state.papers.length === 0) {
            var empty = el("div", "empty-state");
            empty.appendChild(el("strong", null, "还没有论文"));
            empty.appendChild(el("span", null, "请在上方上传 PDF 文件。"));
            host.appendChild(empty);
            return;
        }

        if (papers.length === 0) {
            var noMatch = el("div", "empty-state");
            noMatch.appendChild(el("strong", null, "没有匹配的论文"));
            noMatch.appendChild(el("span", null, "请调整搜索关键词或状态筛选条件。"));
            host.appendChild(noMatch);
            return;
        }

        var table = el("table", "data-table");
        var thead = el("thead");
        var headRow = el("tr");

        ["论文", "作者 / 年份", "状态", "上传时间", "操作"].forEach(function (label) {
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

            var metaCell = el("td");
            metaCell.appendChild(el("span", "cell-title", paper.authors || "—"));
            metaCell.appendChild(el("span", "cell-sub", paper.publication_year || "年份未填写"));
            row.appendChild(metaCell);

            var statusCell = el("td");
            statusCell.appendChild(statusBadge(paper.status));
            row.appendChild(statusCell);

            row.appendChild(el("td", null, formatTime(paper.created_at)));
            row.appendChild(buildActionCell(paper));

            tbody.appendChild(row);
        });

        table.appendChild(thead);
        table.appendChild(tbody);
        host.appendChild(table);
    }

    function loadPapers() {
        renderLoading();

        return api().get("/api/papers/?limit=100", { timeout: 20000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success" || !Array.isArray(payload.data)) {
                    throw new Error((payload && payload.message) || "论文列表返回格式异常");
                }

                hideAlert();
                state.papers = payload.data;
                renderTable();
            })
            .catch(function (error) {
                state.papers = [];
                renderLoadError(error && error.message ? error.message : "论文列表请求失败");
            });
    }

    /* ============================ 文件上传 ============================ */

    function validateFile(file) {
        if (!file) {
            return "请选择要上传的 PDF 文件。";
        }

        if (!/\.pdf$/i.test(file.name)) {
            return "仅支持 PDF 文件。";
        }

        if (file.size === 0) {
            return "不能上传空文件。";
        }

        if (file.size > MAX_FILE_SIZE) {
            return "文件大小为 " + formatSize(file.size) + "，超过 30 MiB 限制。";
        }

        return null;
    }

    function updateFileHint(file) {
        var hint = document.getElementById("fileHint");

        if (!hint) {
            return;
        }

        if (!file) {
            hint.textContent = "尚未选择文件";
            return;
        }

        hint.textContent = file.name + " · " + formatSize(file.size);
    }

    function selectFile(file) {
        var error = validateFile(file);

        if (error) {
            state.selectedFile = null;
            updateFileHint(null);

            var input = document.getElementById("fileInput");

            if (input) {
                input.value = "";
            }

            showAlert(error);
            return;
        }

        hideAlert();
        state.selectedFile = file;
        updateFileHint(file);
    }

    function clearFileSelection() {
        state.selectedFile = null;

        var input = document.getElementById("fileInput");

        if (input) {
            input.value = "";
        }

        updateFileHint(null);
    }

    function uploadPaper(event) {
        event.preventDefault();

        if (state.busy) {
            return;
        }

        if (!state.selectedFile) {
            showAlert("请先选择要上传的 PDF 文件。");
            return;
        }

        var formData = new FormData();
        formData.append("file", state.selectedFile);

        setBusy(true);
        hideAlert();
        showNotice("上传中：", "正在上传 " + state.selectedFile.name + "…", false);

        api().post("/api/papers/upload", formData, { timeout: 180000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success") {
                    throw new Error((payload && payload.message) || "上传失败");
                }

                var paper = payload.data || {};
                showNotice("上传成功：", "《" + (paper.title || "未命名论文") + "》已创建，状态为待处理。", true);
                clearFileSelection();
                return loadPapers();
            })
            .catch(function (error) {
                hideNotice();
                showAlert(error && error.message ? error.message : "上传失败");
            })
            .finally(function () {
                setBusy(false);
            });
    }

    /* ============================ 行操作 ============================ */

    function findPaper(id) {
        return state.papers.filter(function (item) {
            return item.id === id;
        })[0] || null;
    }

    function runProcess(paper) {
        setBusy(true);
        hideAlert();
        showNotice("解析中：", "正在解析《" + paper.title + "》的 PDF 并生成文本块，请勿关闭页面…", false);

        api().post("/api/papers/" + paper.id + "/process", null, { timeout: 300000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success") {
                    throw new Error((payload && payload.message) || "解析失败");
                }

                var data = payload.data || {};
                showNotice(
                    "解析完成：",
                    "共 " + (data.page_count ?? "—") + " 页，"
                        + (data.chunk_count ?? "—") + " 个文本块，"
                        + (data.total_characters ?? "—") + " 个字符。下一步请执行「向量入库」。",
                    true
                );

                return loadPapers();
            })
            .catch(function (error) {
                hideNotice();
                showAlert(error && error.message ? error.message : "PDF 解析失败");
                return loadPapers();
            })
            .finally(function () {
                setBusy(false);
            });
    }

    function runIndex(paper) {
        setBusy(true);
        hideAlert();
        showNotice("入库中：", "正在为《" + paper.title + "》生成向量并写入 ChromaDB，请勿关闭页面…", false);

        api().post("/api/papers/" + paper.id + "/index", null, { timeout: 600000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success") {
                    throw new Error((payload && payload.message) || "向量化入库失败");
                }

                var data = payload.data || {};
                showNotice(
                    "入库完成：",
                    "已写入 " + (data.indexed_count ?? "—") + " 条向量（模型 "
                        + (data.embedding_model || "未知") + "，"
                        + (data.embedding_time_ms ?? "—") + " ms）。",
                    true
                );
            })
            .catch(function (error) {
                hideNotice();
                showAlert(error && error.message ? error.message : "向量化入库失败");
            })
            .finally(function () {
                setBusy(false);
            });
    }

    function openEdit(paper) {
        state.editingId = paper.id;

        document.getElementById("editTitle").value = paper.title || "";
        document.getElementById("editAuthors").value = paper.authors || "";
        document.getElementById("editYear").value = paper.publication_year || "";
        document.getElementById("editAbstract").value = paper.abstract || "";

        if (editModal) {
            editModal.show();
        }
    }

    function saveEdit(event) {
        event.preventDefault();

        if (!state.editingId) {
            return;
        }

        var title = document.getElementById("editTitle").value.trim();
        var authors = document.getElementById("editAuthors").value.trim();
        var yearRaw = document.getElementById("editYear").value.trim();
        var abstract = document.getElementById("editAbstract").value.trim();

        if (!title) {
            showAlert("论文标题不能为空。");
            return;
        }

        var payload = {
            title: title,
            authors: authors || null,
            abstract: abstract || null,
            publication_year: yearRaw === "" ? null : Number(yearRaw)
        };

        var button = document.getElementById("saveEditBtn");
        button.disabled = true;
        button.textContent = "保存中…";

        api().patch("/api/papers/" + state.editingId, payload, { timeout: 20000 })
            .then(function (result) {
                if (!result || result.status !== "success") {
                    throw new Error((result && result.message) || "保存失败");
                }

                hideAlert();

                if (editModal) {
                    editModal.hide();
                }

                showNotice("保存成功：", "论文信息已更新。", true);
                return loadPapers();
            })
            .catch(function (error) {
                showAlert(error && error.message ? error.message : "保存失败");
            })
            .finally(function () {
                button.disabled = false;
                button.textContent = "保存修改";
            });
    }

    function deletePaper(paper) {
        var confirmed = window.confirm(
            "确定删除《" + paper.title + "》吗？\n"
            + "论文记录、文本块、问答记录、阅读报告、向量库记录与 PDF 文件将一并删除，且不可恢复。"
        );

        if (!confirmed) {
            return;
        }

        setBusy(true);
        hideAlert();

        api().del("/api/papers/" + paper.id, { timeout: 30000 })
            .then(function (payload) {
                if (!payload || payload.status !== "success") {
                    throw new Error((payload && payload.message) || "删除失败");
                }

                showNotice("删除成功：", "《" + paper.title + "》已删除。", true);
                return loadPapers();
            })
            .catch(function (error) {
                showAlert(error && error.message ? error.message : "删除失败");
            })
            .finally(function () {
                setBusy(false);
            });
    }

    /* ============================ 事件绑定 ============================ */

    function handleTableClick(event) {
        var button = event.target.closest("[data-action]");

        if (!button) {
            return;
        }

        if (state.busy) {
            showAlert("上一个操作尚未完成，请稍候。");
            return;
        }

        var action = button.getAttribute("data-action");
        var paper = findPaper(Number(button.getAttribute("data-id")));

        if (!paper) {
            showAlert("论文不存在，请刷新列表后重试。");
            return;
        }

        if (action === "process") {
            runProcess(paper);
        } else if (action === "index") {
            runIndex(paper);
        } else if (action === "edit") {
            openEdit(paper);
        } else if (action === "delete") {
            deletePaper(paper);
        }
    }

    function initDropzone() {
        var dropzone = document.getElementById("dropzone");
        var input = document.getElementById("fileInput");

        if (!dropzone || !input) {
            return;
        }

        input.addEventListener("change", function () {
            selectFile(input.files && input.files[0]);
        });

        ["dragenter", "dragover"].forEach(function (name) {
            dropzone.addEventListener(name, function (event) {
                event.preventDefault();
                dropzone.classList.add("is-dragover");
            });
        });

        ["dragleave", "drop"].forEach(function (name) {
            dropzone.addEventListener(name, function (event) {
                event.preventDefault();
                dropzone.classList.remove("is-dragover");
            });
        });

        dropzone.addEventListener("drop", function (event) {
            var files = event.dataTransfer && event.dataTransfer.files;

            if (files && files.length > 0) {
                selectFile(files[0]);
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!window.LitApi) {
            showAlert("请求模块未加载，请检查静态资源是否正常");
            return;
        }

        var modalElement = document.getElementById("editModal");

        if (modalElement && window.bootstrap) {
            editModal = new window.bootstrap.Modal(modalElement);
        }

        initDropzone();

        document.getElementById("uploadForm").addEventListener("submit", uploadPaper);
        document.getElementById("clearFileBtn").addEventListener("click", clearFileSelection);
        document.getElementById("refreshBtn").addEventListener("click", function () {
            if (!state.busy) {
                loadPapers();
            }
        });

        document.getElementById("editForm").addEventListener("submit", saveEdit);

        var searchInput = document.getElementById("searchInput");
        searchInput.addEventListener("input", function () {
            state.keyword = searchInput.value;
            renderTable();
        });

        var statusFilter = document.getElementById("statusFilter");
        statusFilter.addEventListener("change", function () {
            state.status = statusFilter.value;
            renderTable();
        });

        var tableWrap = document.getElementById("papersTableWrap");
        tableWrap.addEventListener("click", handleTableClick);

        loadPapers();
    });
})();
