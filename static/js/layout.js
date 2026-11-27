/**
 * 统一布局交互：移动端侧边栏开合 + 后端健康状态指示。
 */
(function () {
    "use strict";

    function initSidebar() {
        var sidebar = document.getElementById("appSidebar");
        var mask = document.getElementById("appMask");
        var button = document.getElementById("appMenuBtn");

        if (!sidebar || !mask || !button) {
            return;
        }

        function closeSidebar() {
            sidebar.classList.remove("is-open");
            mask.classList.remove("is-visible");
        }

        function toggleSidebar() {
            var isOpen = sidebar.classList.toggle("is-open");
            mask.classList.toggle("is-visible", isOpen);
        }

        button.addEventListener("click", toggleSidebar);
        mask.addEventListener("click", closeSidebar);

        window.addEventListener("resize", function () {
            if (window.innerWidth > 991.98) {
                closeSidebar();
            }
        });
    }

    function renderStatus(state, text) {
        var container = document.getElementById("appStatus");

        if (!container) {
            return;
        }

        var dot = container.querySelector(".status-dot");
        var label = container.querySelector(".status-text");

        if (dot) {
            dot.className = "status-dot" + (state ? " " + state : "");
        }

        if (label) {
            label.textContent = text;
        }
    }

    function checkBackend() {
        if (!window.LitApi) {
            renderStatus("is-error", "请求模块未加载");
            return;
        }

        renderStatus("is-pending", "后端状态检测中");

        window.LitApi.get("/api/health", { timeout: 8000 })
            .then(function (payload) {
                if (payload && payload.status === "ok") {
                    renderStatus("is-ok", "后端运行正常");
                } else {
                    renderStatus("is-error", "后端返回异常状态");
                }
            })
            .catch(function (error) {
                renderStatus("is-error", error && error.message
                    ? error.message
                    : "后端不可用");
            });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initSidebar();
        checkBackend();
    });
})();
