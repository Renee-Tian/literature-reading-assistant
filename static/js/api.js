/**
 * 统一 API 请求封装。
 *
 * 约定：
 * 1. 只负责发起请求、解析 JSON、抛出可读错误，不包含任何业务判断。
 * 2. 后端返回 {status, data, message} 结构时原样返回，由调用方决定如何渲染。
 */
(function () {
    "use strict";

    var DEFAULT_TIMEOUT = 30000;

    function ApiError(message, status, payload) {
        this.name = "ApiError";
        this.message = message;
        this.status = status || 0;
        this.payload = payload || null;
    }

    ApiError.prototype = Object.create(Error.prototype);
    ApiError.prototype.constructor = ApiError;

    function buildHeaders(headers, body) {
        var result = Object.assign({ Accept: "application/json" }, headers || {});

        // FormData 由浏览器自动设置 multipart 边界
        if (body && !(body instanceof FormData) && !result["Content-Type"]) {
            result["Content-Type"] = "application/json";
        }

        return result;
    }

    function normalizeBody(body) {
        if (body === null || body === undefined) {
            return null;
        }

        if (body instanceof FormData) {
            return body;
        }

        if (typeof body === "string") {
            return body;
        }

        return JSON.stringify(body);
    }

    function request(path, options) {
        var config = options || {};
        var timeout = typeof config.timeout === "number" ? config.timeout : DEFAULT_TIMEOUT;
        var controller = new AbortController();
        var timer = setTimeout(function () {
            controller.abort();
        }, timeout);

        var fetchOptions = {
            method: config.method || "GET",
            headers: buildHeaders(config.headers, config.body),
            credentials: "same-origin",
            signal: controller.signal
        };

        var body = normalizeBody(config.body);

        if (body !== null && fetchOptions.method !== "GET") {
            fetchOptions.body = body;
        }

        return fetch(path, fetchOptions)
            .then(function (response) {
                return response.text().then(function (text) {
                    var payload = null;

                    if (text) {
                        try {
                            payload = JSON.parse(text);
                        } catch (error) {
                            payload = null;
                        }
                    }

                    if (!response.ok) {
                        var message = payload && payload.message
                            ? payload.message
                            : "请求失败（HTTP " + response.status + "）";

                        throw new ApiError(message, response.status, payload);
                    }

                    if (payload === null) {
                        throw new ApiError("服务返回了无法解析的数据", response.status, null);
                    }

                    return payload;
                });
            })
            .catch(function (error) {
                if (error && error.name === "AbortError") {
                    throw new ApiError("请求超时，请确认后端服务是否正常运行", 0, null);
                }

                if (error instanceof ApiError) {
                    throw error;
                }

                throw new ApiError(
                    "网络请求失败，请检查后端服务与网络连接",
                    0,
                    null
                );
            })
            .finally(function () {
                clearTimeout(timer);
            });
    }

    window.LitApi = {
        ApiError: ApiError,
        request: request,
        get: function (path, options) {
            return request(path, Object.assign({}, options, { method: "GET" }));
        },
        post: function (path, body, options) {
            return request(path, Object.assign({}, options, { method: "POST", body: body }));
        },
        patch: function (path, body, options) {
            return request(path, Object.assign({}, options, { method: "PATCH", body: body }));
        },
        del: function (path, options) {
            return request(path, Object.assign({}, options, { method: "DELETE" }));
        }
    };
})();
